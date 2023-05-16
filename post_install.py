import platform
import subprocess

platform_commands = {
    'Linux': {
        'command': ['sudo', 'apt-get', 'install', '-y', 'libmagic1'],
        'message': 'Failed to install libmagic1. Please install it manually with command: sudo apt-get install libmagic1',
    },
    'Windows': {
        'command': ['pip', 'install', 'python-magic-bin'],
        'message': 'Failed to install python-magic-bin. Please install it manually with command: pip install python-magic-bin',
    },
    'Darwin': {
        'command': ['brew', 'install', 'libmagic'],
        'message': 'Failed to install libmagic. Please install it manually with command: brew install libmagic',
    },
}

current_system = platform.system()

if current_system in platform_commands:
    command_info = platform_commands[current_system]
    try:
        subprocess.run(command_info['command'], check=True)
    except subprocess.CalledProcessError:
        print(command_info['message'])
