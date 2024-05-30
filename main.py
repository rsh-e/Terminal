
import os
import msvcrt
import json
import hashlib
import secrets
import getpass
import sys
import socket
import difflib
import threading
import time

class Editor:
    def __init__(self):
        self.text = ""

    def open_editor(self):
        print("Editor is now open. Type ':q' to exit.")
        while True:
            user_input = input()
            if ":q" in user_input:
                index = user_input.index(":q")
                self.text += user_input[:index] + "\n"
                break
            self.text += user_input + "\n"

class File:
    # Initialize a new file with a name and some text
    def __init__(self, name, text):
        self.name = name  # The name of the file
        self.text = text  # The contents of the file

# Define a class to represent a folder
class Folder:
    # Initialize a new folder with a name
    def __init__(self, name):
        self.name = name  # The name of the folder
        self.contents = []  # A list of files and folders inside this folder
        self.parent_directory = None

    # Add a file or folder to the current folder
    def add_to_folder(self, folder):
        self.contents.append(folder)  # Append the new file or folder to the list of contents

    # Display the folder structure in a tree-like format
    def display(self, indent=0, is_last=True):
        connector = '└── ' if is_last else '├── '
        print('  ' * indent + connector + self.name)
        for i, content in enumerate(self.contents):
            is_last_content = i == len(self.contents) - 1
            if isinstance(content, Folder):
                content.display(indent + 1, is_last_content)
            else:
                connector = '└── ' if is_last_content else '├── '
                print('  ' * (indent + 1) + connector + content.name + '.txt')

    # Count the number of files and folders in the folder structure
    def count_files_and_folders(self):
        files = 0  
        folders = 1  
        for content in self.contents:  
            if isinstance(content, Folder):  
                sub_files, sub_folders = content.count_files_and_folders()  
                files += sub_files  
                folders += sub_folders  
            else:  
                files += 1  
        return files, folders  
    
    def is_in_recycle_bin(self):
        current = self
        while current is not None:
            if current.name == "recycle_bin":
                return True
            current = current.parent_directory
        return False


class LoginSystem:
    def __init__(self):
        # Initialize the login system by loading existing users from a JSON file.
        self.users = self.load_users()

    def login(self, username, password):
        # Check if a user with the given username and password exists in the system.
        for user in self.users:
            if user['username'] == hashlib.sha256(username.encode()).hexdigest():
                if user['password'] == self.hash_password(password, bytes.fromhex(user['salt'])):
                    return True
        return False

    def register(self, username, password, confirm_password):
    # Register a new user with the given username and password.
        if password != confirm_password:
            print("Passwords do not match. Please try again.")
            return False

        if len(password) < 5:
            print("Password is too short. It should be at least 5 characters long.")
            return False

        if not any(char.isupper() for char in password):
            print("Password should have at least one upper case letter.")
            return False

        if not any(char.islower() for char in password):
            print("Password should have at least one lower case letter.")
            return False

        if not any(char.isdigit() for char in password):
            print("Password should have at least one number.")
            return False

        for user in self.users:
            if user['username'] == hashlib.sha256(username.encode()).hexdigest():
                print("Username already exists. Please choose a different username.")
                return False

        salt = secrets.token_bytes(16).hex()
        hashed_password = self.hash_password(password, bytes.fromhex(salt))
        self.users.append({
            'username': hashlib.sha256(username.encode()).hexdigest(),
            'password': hashed_password,
            'salt': salt
        })
        self.save_users()
        print("Registration successful!")
        return True
    
    def is_strong_password(self, password):
        # Check if the password is at least 5 characters long
        if len(password) < 5:
            return False

        # Check if the password has at least 1 upper case letter, 1 lower case letter and 1 number
        if not any(char.isupper() for char in password):
            return False
        if not any(char.islower() for char in password):
            return False
        if not any(char.isdigit() for char in password):
            return False

        return True

    def run(self):
        while True:
            print("Options:")
            print("1. Login")
            print("2. Register")
            choice = input("Enter your choice: ")
            if choice == "1":
                username = input("Enter your username: ")
                password = get_password("Enter your password: ")
                if self.login(username, password):
                    print("Login successful!")
                    terminal = Terminal(username)
                    if not terminal.run():
                        continue  # Go back to the start of the loop
                else:
                    print("Invalid username or password. Please try again.")
            elif choice == "2":
                username = input("Enter your desired username: ")
                password = get_password("Enter your desired password: ")  # Use getpass here
                confirm_password = get_password("Confirm your password: ")  # Use getpass here
                if self.register(username, password, confirm_password):
                    print("Registration successful!")
            else:
                print("Invalid choice. Please try again.")

    def load_users(self):
        # Load existing users from a JSON file named 'users.json'.
        try:
            with open('users.json') as f:
                data = json.load(f)
            return data['users']
        except FileNotFoundError:
            # If the file doesn't exist, return an empty list.
            return []

    def save_users(self):
        # Save the current state of users to the 'users.json' file.
        with open('users.json', 'w') as f:
            json.dump({'users': self.users}, f)

    def hash_password(self, password, salt):
        # Hash a password using PBKDF2 with HMAC-SHA256.
        # This is a secure way to store passwords.
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()

    def login(self, username, password):
        # Check if a user with the given username and password exists in the system.
        for user in self.users:
            if user['username'] == hashlib.sha256(username.encode()).hexdigest():
                if user['password'] == self.hash_password(password, bytes.fromhex(user['salt'])):
                    return True
        return False


class Terminal:
    def __init__(self, username):
        self.line_number = 1
        self.user = username
        self.current_directory = Folder("root")  # Initialize the current directory to a root folder
        self.current_directory.parent_directory = None
        self.root_directory = self.current_directory  # Store the root directory for later use
        self.recycle_bin = Folder("recycle_bin")  # Create a new recycle bin directory
        self.root_directory.add_to_folder(self.recycle_bin)  # Add the recycle bin to the root directory
        self.recycle_bin_contents = {}
        self.running = True
        self.recycle_bin_thread = threading.Thread(target=self.check_recycle_bin)
        self.recycle_bin_thread.start()

    def get_line(self):
        print(f"\033[1;30m@{self.user}\033[0m \033[1;34m[{self.line_number}]\033[0m \033[1;32m${self.current_directory.name}\033[0m:", end=' ', flush=True)
        line = ''
        while True:
            char = msvcrt.getwch()
            if char == '\r':  # Enter key
                print('\n', end='', flush=True)  # Move to a new line
                break
            elif char == '\b':  # Backspace key
                if line:
                    print('\b \b', end='', flush=True)  # Erase the last character
                    line = line[:-1]
            elif char == ' ' and line.strip() != '':
                print('\033[0m', end='', flush=True)  # Reset color to default
                line += char
                print(char,end='', flush=True)
            elif line.strip() == '':
                print('\033[93m', end='', flush=True)  # Set color to yellow
                line += char
                print(char, end='', flush=True)
            else:
                line += char
                print(char, end='', flush=True)
        self.line_number += 1  # Increment line number here
        return line.strip()

    def exit_command(self):
        print("Exiting terminal.")
        print('\033[0m', end='', flush=True)  # Reset color to default
        os._exit(0)

    def cls_command(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def logout_command(self):
        print("Logging out.")
        print('\033[0m', end='', flush=True)  # Reset color to default
        LoginSystem.run(self)
        #return False  # Return False to signal that we want to exit the terminal

    def mkdir_command(self, line):
        folder_name = line[6:]  # Get the folder name from the command
        if folder_name:  # Check if a folder name was provided
            if self.current_directory.name == "recycle_bin":
                print("Cannot create folders in the recycle bin.")
            else:
                new_folder = Folder(folder_name)
                self.current_directory.add_to_folder(new_folder)
                print(f"Folder '{folder_name}' created successfully.")
        else:
            print("Please provide a folder name.")

    def tree_command(self, line):
        args = line.split()
        if len(args) == 1:  # If only 'tree' is typed
            self.current_directory.display()
        elif len(args) == 2 and args[1] == 'root':  # If 'tree root' is typed
            self.root_directory.display()
        else:
            print("Invalid command")

    def help_command(self):
        commands = {
            "cls": "Clear the screen",
            "exit": "Exit the terminal",
            "help": "Display this help message",
            "logout": "Log out of the terminal",
            "mkdir": "Create a new directory",
            "tree": "Display the directory structure",
            "yosdadasdas": "nothing"
        }

        max_length = max(len(command) for command in commands)

        print("Available commands:")
        for command, description in commands.items():
            print(f"{command}: {'-' * (max_length - len(command))}----  {description}")

    def whoami_command(self):
        import socket
        ipv4_address = socket.gethostbyname(socket.gethostname())
        print(f"You are {self.user} at {ipv4_address}")
    
    def cat_command(self, line):
        file_name = ""  # Get the file name from the command
        for i in line[4:]:
            if i == " ":
                break
            else:
                file_name = file_name + i   
        command = line[-2] + line[-1]
        if file_name:  # Check if a file name was provided
            existing_file = self.find_file(file_name)
            if existing_file:
                if command in ['-v', '-e', '-o']:
                    if command == '-v':
                        print(existing_file.text)
                    elif command == '-e':
                        import pyperclip
                        pyperclip.copy(existing_file.text)
                        editor = Editor()
                        print("Editor is now open. Type ':q' to exit.")
                        print("Paste the contents of the file and edit it as needed.")
                        while True:
                            user_input = input()
                            if ":q" in user_input:
                                index = user_input.index(":q")
                                editor.text += user_input[:index] + "\n"
                            editor.text += user_input + "\n"
                        existing_file.text = editor.text
                    elif command == '-o':
                        editor = Editor()
                        editor.open_editor()
                        existing_file.text = editor.text
                else:
                    print(f"File '{file_name}' already exists.")
                    while True:
                        action = input("Enter '-v' to view, '-e' to edit, or '-o' to override: ")
                        if action == '-v':
                            print(existing_file.text)
                            break
                        elif action == '-e':
                            import pyperclip
                            pyperclip.copy(existing_file.text)
                            editor = Editor()
                            print("Editor is now open. Type ':q' to exit.")
                            print("Paste the contents of the file and edit it as needed.")
                            while True:
                                user_input = input()
                                if ":q" in user_input:
                                    index = user_input.index(":q")
                                    editor.text += user_input[:index] + "\n"
                                    break
                                editor.text += user_input + "\n"
                            existing_file.text = editor.text
                            break
                        elif action == '-o':
                            editor = Editor()
                            editor.open_editor()
                            existing_file.text = editor.text
                            break
                        else:
                            print("Invalid option. Please try again.")
            else:
                editor = Editor()
                editor.open_editor()
                new_file = File(file_name, editor.text)  # Create a new file with the text from the editor
                self.current_directory.add_to_folder(new_file)  # Add the file to the current directory
                print(f"File '{file_name}' created successfully.")
        else:
            print("Please provide a file name.")

    def find_file(self, file_name):
        for item in self.current_directory.contents:
            if isinstance(item, File) and item.name == file_name:
                return item
        return None

    def cd_command(self, line):
        directory_to_switch = line[3:]
        if directory_to_switch == "..":
            if self.current_directory.name == "root":
                print("You are currently in the root directory and you cannot go back")
            else:
                self.current_directory = self.current_directory.parent_directory
                return
        else:
            for content in self.current_directory.contents:
                if isinstance(content, Folder) and content.name == directory_to_switch:
                    content.parent_directory = self.current_directory
                    self.current_directory = content
                    return
            print(f"Directory '{directory_to_switch}' not found.")
    
    def suggest_similar_names(self, old_name):
        similar_names = difflib.get_close_matches(old_name, [content.name for content in self.current_directory.contents], n=1, cutoff=0.5)
        return similar_names
        
    def rname_command(self, line):
        parts = line.split()
        if len(parts) != 3:
            print("Invalid syntax. Usage: rname old_name new_name")
            return
        _, old_name, new_name = parts
        for content in self.current_directory.contents:
            if content.name == new_name:
                print(f"A file or folder with the name '{new_name}' already exists.")
                return
            elif content.name == old_name:
                content.name = new_name
                print(f"Successfully renamed '{old_name}' to '{new_name}'.")
                return
        similar_names = self.suggest_similar_names(old_name)
        if similar_names:
            print(f"No such file or folder '{old_name}'. Did you mean: {similar_names[0]}")
        else:
            print(f"No such file or folder '{old_name}'.")
    
    def ls_command(self, line):
        contents = [(content.name, "directory" if isinstance(content, Folder) else "file") for content in self.current_directory.contents]
        if len(contents) == 0:
            print("No files or directories present")
        else:
            max_length = max(len(name) for name, _ in contents)

            print("Contents of current directory:")
            for name, type in contents:
                print(f"{name} {'-' * (max_length - len(name))}----  {type}")

    def check_recycle_bin(self):
        while self.running:
            current_time = time.time()
            for content, move_time in list(self.recycle_bin_contents.items()):
                if current_time - move_time > 120:  # 120 seconds = 2 minutes
                    self.recycle_bin.contents.remove(content)
                    del self.recycle_bin_contents[content]
            time.sleep(1)  # Check every second

    def rm_command(self, line):
        _, object_to_delete = line.split()
        if object_to_delete == "recycle_bin":
            print("Cannot delete the recycle bin")
            return 
        for content in self.current_directory.contents:
            if content.name == object_to_delete:
                if self.current_directory == self.recycle_bin:  # Check if we're currently in the recycle bin
                    prompt = f"Are you sure you want to delete '{object_to_delete}'? This will permanently delete it. (y/n): "
                else:
                    prompt = f"Are you sure you want to delete '{object_to_delete}'? This will move the file to the recycle bin. (y/n): "
                
                response = input(prompt)
                if response.lower() == 'y':
                    if content in self.current_directory.contents:
                        self.current_directory.contents.remove(content)
                    if self.current_directory != self.recycle_bin:  # Only move to recycle bin if we're not already in it
                        self.recycle_bin.add_to_folder(content)
                        self.recycle_bin_contents[content] = time.time()
                        print(f"'{object_to_delete}' has been moved to the recycle bin.")
                    else:
                        if content in self.recycle_bin_contents:
                            del self.recycle_bin_contents[content]
                        print(f"'{object_to_delete}' has been permanently deleted.")
                elif response.lower() == 'n':
                    print("Deletion cancelled.")
                else:
                    print("Invalid response. Deletion cancelled.")
                return
        print(f"The file '{object_to_delete}' does not exist.")
            
    def cp_command(self, line):
        _, object_to_copy, destination = line.split()
        location = None
        # Search for the object to copy in the current directory
        for content in self.current_directory.contents:
            if content.name == object_to_copy:
                location = content
                break

        if location:
            # Search for the destination folder in the entire root directory
            destination_folder = self.find_object(self.root_directory, destination)

            if destination_folder and isinstance(destination_folder, Folder):
                destination_folder.add_to_folder(location)
            else:
                print(f"Destination '{destination}' not found.")
        else:
            print(f"'{object_to_copy}' not found.")
    
    def mv_command(self, line):
        _, object_to_move, destination = line.split()
        location = None
        # Search for the object to move in the current directory
        for content in self.current_directory.contents:
            if content.name == object_to_move:
                location = content
                break

        if location:
            # Search for the destination folder in the entire root directory
            destination_folder = self.find_object(self.root_directory, destination)

            if destination_folder and isinstance(destination_folder, Folder):
                # Add the object to the destination folder
                destination_folder.add_to_folder(location)
                # Remove the object from its original location
                self.current_directory.contents.remove(location)
            else:
                print(f"Destination '{destination}' not found.")
        else:
            print(f"'{object_to_move}' not found.")

    # Helper function to find an object in a folder and its subdirectories
    def find_object(self, folder, object_name):
        for content in folder.contents:
            if content.name == object_name:
                return content
            elif isinstance(content, Folder):
                result = self.find_object(content, object_name)
                if result:
                    return result
        return None
    
    def empty_command(self):
        if self.current_directory.name == "recycle_bin":
            confirm = input("Are you sure you want to permanently deleted ALL files and folders? (y/n): ")
            if confirm.lower() == "y":
                self.recycle_bin.contents = []
                print("All files and folders in the recycle bin have been deleted")
            else:
                print("Nothing has been deleted")
        else:
            confirm = input("Are you sure you want to move ALL files and folders into the recycle bin? (y/n): ")
            if confirm.lower() == "y":
                for content in self.current_directory.contents[:]:
                    # Check if a file or folder with the same name already exists in the recycle bin
                    existing_content = next((c for c in self.recycle_bin.contents if c.name == content.name), None)
                    if existing_content:
                        print(f"A file or folder with the name '{content.name}' already exists in the recycle bin. Renaming...")
                        # You could implement a better renaming strategy here
                        content.name += "_1"
                    self.recycle_bin.add_to_folder(content)
                    self.recycle_bin_contents[content] = time.time()
                self.current_directory.contents = []
                print(f'All files and folders in {self.current_directory.name} have been moved to the recycle bin.')
            else:
                print("Nothing has been deleted.")
        return

    def restore_command(self, line):
        if self.current_directory != self.recycle_bin:
            print("You can only restore files from the recycle bin.")
            return
        _, object_to_restore = line.split()
        for content in self.recycle_bin.contents:
            if content.name == object_to_restore:
                parent_directory = content.parent_directory
                self.recycle_bin.contents.remove(content)
                parent_directory.add_to_folder(content)
                print(f"'{object_to_restore}' has been restored to its original location.")
                return
        print(f"The file '{object_to_restore}' does not exist in the recycle bin.")
    

    def find_file(self, filename):
        return self.find_file_recursive(self.current_directory, filename)

    def find_file_recursive(self, directory, filename):
        for content in directory.contents:
            if isinstance(content, File) and content.name == filename:
                return content
            elif isinstance(content, Folder):
                file = self.find_file_recursive(content, filename)
                if file:
                    return file
        return None
    
    def bash_command(self, line):
        filename = line[5:].strip()  # Extract the filename from the command
        try:
            with open(filename + '.txt', 'r') as file:
                for line in file:
                    line = line.strip()
                    if line:  # Ignore empty lines
                        print(f"\033[1;30m@{self.user}\033[0m \033[1;34m[{self.line_number}]\033[0m \033[1;32m${self.current_directory.name}\033[0m:", line, end='\n', flush=True)  # Print the prompt with correct formatting and increment line number
                        self.execute(line)
                        self.line_number = self.line_number + 1
        except FileNotFoundError:
            print(f"File '{filename}.txt' not found.")


    def execute(self, line):
        if line.lower() == 'exit':
            self.exit_command()
            #sys.exit(0)
        elif line.lower() == 'cls':
            self.cls_command()
        elif line.lower() == 'logout':
            self.logout_command()
        elif line.lower().startswith('mkdir'):
            self.mkdir_command(line)
        elif line.lower().startswith('tree'):
            self.tree_command(line)
        elif line.lower() == 'help':
            self.help_command()
        elif line.lower() == 'whoami':
            self.whoami_command()   
        elif line.lower().startswith('cat'):
            self.cat_command(line)
        elif line.lower().startswith('cd'):
            self.cd_command(line)
        elif line.lower().startswith('rname'):
            self.rname_command(line)
        elif line.lower() == 'ls':
            self.ls_command(line)
        elif line.lower().startswith('rm'):
            self.rm_command(line)
        elif line.lower().startswith('cp'):
            self.cp_command(line)
        elif line.lower().startswith('mv'):
            self.mv_command(line)
        elif line.lower() == 'empty':
            self.empty_command()
        elif line.lower().startswith('restore'):
            self.restore_command(line)
        elif line.lower().startswith('bash'):
            self.bash_command(line)
        else:
            # Fuzzy matching
            available_commands = ['exit', 'cls', 'logout', 'mkdir', 'tree', 'help', 'whoami', 'cat']
            close_matches = difflib.get_close_matches(line.lower(), available_commands, n=1, cutoff=0.5)
            if close_matches:
                print(f"Invalid command. Did you mean '{close_matches[0]}'? Type 'help' for a list of available commands.")
            else:
                print("Invalid command. Type 'help' for a list of available commands.")
        #self.line_number += 1

    def run(self):
        while True:
            line = self.get_line()
            if self.execute(line) == False:  # Check if execute returns False
                return  # Exit the run method

def get_password(prompt):
    print(prompt, end='', flush=True)
    password = ''
    while True:
        char = msvcrt.getch()
        if char == b'\r':  # Enter key
            break
        elif char == b'\x08':  # Backspace
            if password:
                password = password[:-1]
                sys.stdout.write('\b \b')  # Remove last character
                sys.stdout.flush()
        else:
            password += char.decode()
            sys.stdout.write('*')
            sys.stdout.flush()
    print()  # Newline
    return password

def main():
    login_system = LoginSystem()
    login_system.run()

if __name__ == "__main__":
    main()
