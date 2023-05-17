import configparser
import tkinter as tk
from tkinter import ttk
import paramiko
import logging
from io import StringIO

# Read the config file
config = configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger()

# Function to execute a command on a remote server
def execute_ssh_command(host, user, key_path, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, key_filename=key_path)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()

        logger.info(f"Executed command: {command} on host: {host}")
        logger.info(f"Output: {output}")

        return output
    except Exception as e:
        logger.error(f"An error occurred while executing the command: {str(e)}")
        return f"Error: {e}"
    finally:
        ssh.close()

# Function to execute a command and display the output in the text widget
def on_command_click(host, user, key_path, command):
    try:
        output = execute_ssh_command(host, user, key_path, command)
        
        if output:
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, output)
        else:
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "The command returned no output.")
    except Exception as e:
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"An error occurred: {str(e)}")

# Function to get server commands
def get_server_commands(server_section):
    commands = []
    for section in config.sections():
        if section.startswith(server_section + '.command'):
            name = config.get(section, 'name')
            command = config.get(section, 'command')
            commands.append((name, command))
    return commands


# COMMAND HANDLER
def create_command_handler(host, user, key_path, cmd):
    def command_handler():
        on_command_click(host, user, key_path, cmd)
    return command_handler

# MAIN WINDOW
root = tk.Tk()
root.title("SSH Command Executor")

# NOTEBOOK WIDGET
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True)

# OUTPUT WIDGET
output_text = tk.Text(root, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, expand=True)

# SHOW SERVERS AND BUTTONS
server_sections = [section for section in config.sections() if not section.startswith(tuple([s + '.command' for s in config.sections()]))]
for section in server_sections:
    server_frame = ttk.Frame(notebook)
    notebook.add(server_frame, text=section)

    host = config.get(section, 'host')
    user = config.get(section, 'user')
    key_path = config.get(section, 'key_path')
    
    commands = get_server_commands(section)

    # BUTTONS
    for index, (button_name, cmd) in enumerate(commands):
        button_section = section + '.command' + str(index + 1)
        button_bg_color = config.get(button_section, 'color', fallback=None)
        button_width = 20
        button_height = 1
        button_grid_x = config.getint(button_section, 'grid_x', fallback=index % 2)
        button_grid_y = config.getint(button_section, 'grid_y', fallback=index // 2)

        button = tk.Button(
            server_frame,
            text=button_name,
            command=create_command_handler(host, user, key_path, cmd),
            bg=button_bg_color,
            width=button_width,
            height=button_height,
        )

        button.grid(row=button_grid_y, column=button_grid_x, padx=5,pady=2)


if __name__ == "__main__":
    root.mainloop()
