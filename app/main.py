import argparse
import os
import sys
import json
import subprocess

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    read_file = {"type": "function",
                 "function": {
                   "name": "Read",
                   "description": "Read and return the contents of a file",
                   "parameters": {
                       "type": "object",
                       "properties": {
                         "file_path": {
                           "type": "string",
                           "description": "The path to the file to read"
                         }
                       },
                       "required": ["file_path"]
                   }
                 }
               }
    
    write_file = {
      "type": "function",
      "function": {
        "name": "Write",
        "description": "Write content to a file",
        "parameters": {
          "type": "object",
          "required": ["file_path", "content"],
          "properties": {
            "file_path": {
              "type": "string",
              "description": "The path of the file to write to"
            },
            "content": {
              "type": "string",
              "description": "The content to write to the file"
            }
          }
        }
      }
    }

    run_bash_command = {
      "type": "function",
      "function": {
        "name": "Bash",
        "description": "Execute a shell command",
        "parameters": {
          "type": "object",
          "required": ["command"],
          "properties": {
            "command": {
              "type": "string",
              "description": "The command to execute"
            }
          }
        }
      }
    }

    messages=[{"role": "user", "content": args.p}]
    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools=[read_file, write_file, run_bash_command]
        )
    
        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")
     
        if chat.choices and chat.choices[0].message:
            message = chat.choices[0].message
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tool_call.model_dump() for tool_call in message.tool_calls or []]
            })
    
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_params = json.loads(tool_call.function.arguments)
                    if function_name == 'Read':
                        file_path = function_params["file_path"]
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except FileNotFoundError:
                            print(f"Error: The file '{file_path}' was not found.")
                        except Exception as e:
                            print(f"An error occured: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": content
                            })    
                    elif function_name == 'Write':
                        file_path = function_params["file_path"]
                        content = function_params["content"]
                        try:
                            with open(file_path, 'a') as f:
                                f.write(content) 
                        except FileNotFoundError:
                            print(f"Error: The file '{file_path}' was not found.")
                        except Exception as e:
                            print(f"An error occured: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": content
                            })    
                    elif function_name == 'Bash':
                        command = function_params["command"]
                        try:
                            completed = subprocess.run(
                            command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            )
                        except subprocess.CalledProcessError as e:
                            print(f"Command failed with return code {e.returncode}")
                            print("STDOUT:", e.stdout)
                            print("STDERR:", e.stderr)
                        except FileNotFoundError:
                            print(f"The executable 'command_name' was not found in the PATH. Ensure '{bash_path_dir}' is correct.")
                            print(command)
                        result = (completed.stdout or "") + (completed.stderr or "")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                            })    
                    else:
                        print("No tool calls were found in the response")
            else:
                print(message.content)
                break

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # TODO: Uncomment the following line to pass the first stage
    # print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
