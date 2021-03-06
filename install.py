print("* Taichi Installer")

import os
import sys
import platform
import argparse
import subprocess
from os import environ
import platform

print(platform.architecture())

# Utils

import struct
assert struct.calcsize('P') * 8 == 64, "Only 64-bit platforms are supported. Current platform: {}".format(struct.calcsize('P') * 8)

if sys.version_info[0] < 3 or sys.version_info[1] < 5:
  print("\nPlease restart with python3. \n(Taichi supports Python 3.5+)\n")
  print("Current version:", sys.version_info)
  exit(-1)

def get_python_executable():
  return sys.executable.replace('\\','/')

def get_shell_name():
  return environ['SHELL'].split('/')[-1]

def get_shell_rc_name():
  shell = get_shell_name()
  if shell == 'bash':
    return '~/.bashrc'
  elif shell == 'zsh':
    return '~/.zshrc'
  else:
    assert False, 'No shell rc file specified for shell "{}"'.format(shell)

def get_username():
  if build_type == 'ci':
    os.environ['TC_CI'] = '1'
    username = 'travis'
  else:
    assert get_os_name() != 'win'
    import pwd
    username = pwd.getpwuid(os.getuid())[0]
  return username

def check_command_existence(cmd):
  return os.system('type {}'.format(cmd)) == 0

def execute_command(line):
  print('Executing command:', line)
  return os.system(line)

def get_os_name():
  name = platform.platform()
  if name.lower().startswith('darwin'):
    return 'osx'
  elif name.lower().startswith('windows'):
    return 'win'
  elif name.lower().startswith('linux'):
    return 'linux'
  assert False, "Unknown platform name %s" % name

def get_default_directory_name():
  osname = get_os_name()
  if osname == 'linux':
    username = get_username()
    return '/home/{}/repos'.format(username)
  elif osname == 'osx':
    username = get_username()
    return '/Users/{}/repos'.format(username)
  else:
    #Windows
    return os.getcwd()

def append_to_shell_rc(line):
  if get_os_name() != 'win':
    execute_command('echo "{}" >> {}'.format(line, get_shell_rc_name()))
  else:
    print("Warning: Windows environment variable persistent edits are not supported")

def set_env(key, val, val_now=None):
  if val_now is None:
    val_now = val
  val = str(val)
  val_now = str(val_now)
  append_to_shell_rc("export {}={}".format(key, val))
  os.environ[key] = val_now

def get_path_separator():
  if get_os_name() == 'win':
    return ';'
  else:
    return ':'

def test_installation():
  return subprocess.run([get_python_executable(), "-c", "import taichi as tc"]).returncode == 0


# (Stateful) Installer class

class Installer:
  def __init__(self):
    parser = argparse.ArgumentParser()
    parser.parse_args()
    self.build_type = None

  def detect_or_setup_repo(self):
    cwd = os.getcwd()
    print("Current directory:", cwd)

    if os.path.exists(os.path.join(cwd, 'include', 'taichi')):
      print("Taichi source detected.")
      self.root_dir = os.path.abspath(os.path.join(cwd, '..'))
    else:
      print("Cloning taichi from github...")
      self.root_dir = get_default_directory_name()
      os.chdir(self.root_dir)
      execute_command('mkdir {}'.format(self.root_dir))
      if os.path.exists('taichi'):
        print('Existing taichi installation detected.')
        print('Please remove existing taichi installation in {}'.format(self.root_dir))
        exit(-1)
      self.root_dir = os.getcwd()
      execute_command('git clone https://github.com/yuanming-hu/taichi.git')
      os.chdir('taichi')
    if os.path.exists('external/lib'):
      print('Existing taichi runtimes detected.')
    else:
      print('Fetching taichi runtimes...')
      if get_os_name() == 'win':
        # On Windows, both MSVC and MinGW are supported. Assuming MSVC here
        # TODO: MinGW
        execute_command('git clone https://github.com/yuanming-hu/taichi_runtime external/lib -b msvc --depth 1'.format(get_os_name()))
      else:
        execute_command('git clone https://github.com/yuanming-hu/taichi_runtime external/lib -b {} --depth 1'.format(get_os_name()))

  def run(self):
    assert get_os_name() in ['linux', 'osx', 'win'], \
      'Platform {} is not currently supported by this script. Please install manually.'.format(get_os_name())
    global build_type
    if len(sys.argv) > 1:
      self.build_type = sys.argv[1]
      print('Build type: ', build_type)
    else:
      build_type = 'default'

    print('Build type = {}'.format(build_type))

    assert build_type in ['default', 'ci']

    check_command_existence('wget')
    try:
      import pip
      print('pip3 installation detected')
    except Exception as e:
      print(e)
      print('Installing pip3')
      execute_command('wget https://bootstrap.pypa.io/get-pip.py')
      subprocess.run([get_python_executable(), "get-pip.py", "--user"])
      execute_command('rm get-pip.py')

    subprocess.run([get_python_executable(), "-m", "pip", "install", "colorama", "numpy", "Pillow", "flask", "scipy", "pybind11", "flask_cors", "GitPython", "yapf", "pyglet", "PyQt5"])
    print("importing numpy test:")
    ret = subprocess.run([get_python_executable(), "-c", "import numpy as np"])
    print("ret:", ret)

    execute_command('cmake --version')
    if get_os_name() == 'osx':
      # Check command existence
      check_command_existence('git')
      check_command_existence('cmake')
      # TODO: ship ffmpeg
      #check_command_existence('ffmpeg')
    elif get_os_name() == 'linux':
      check_command_existence('sudo')
      execute_command('sudo apt-get update')
      # TODO: this works for Ubuntu only
      if build_type == 'ci':
        execute_command('sudo apt-get install -y dev python3-tk')
      else:
        execute_command('sudo apt-get install -y python3-dev git build-essential cmake make g++ python3-tk')

    self.detect_or_setup_repo()


    #TODO: Make sure there is no existing Taichi ENV
    set_env('TAICHI_NUM_THREADS', 8)
    set_env('TAICHI_ROOT_DIR', self.root_dir)

    set_env('PYTHONPATH', '$TAICHI_ROOT_DIR/taichi/python/' + get_path_separator() + '$PYTHONPATH',
            '{}/taichi/python/'.format(self.root_dir) + get_path_separator() + os.environ.get('PYTHONPATH', ''))
    set_env('PATH', '$TAICHI_ROOT_DIR/taichi/bin/' + get_path_separator() + '$PATH', os.path.join(self.root_dir, 'taichi/bin') + get_path_separator() + os.environ.get('PATH', ''))

    os.environ['PYTHONIOENCODING'] = 'utf-8'
    print('PYTHONPATH={}'.format(os.environ['PYTHONPATH']))

    execute_command('echo $PYTHONPATH')

    if test_installation():
      print('  Successfully Installed Taichi at {}.'.format(self.root_dir))
      if get_os_name() != 'win':
        if execute_command('ti') != 0:
          print('  Warning: shortcut "ti" does not work.')
        if execute_command('taichi') != 0:
          print('  Warning: shortcut "taichi" does not work.')
        print('  Please execute')
        print('    source ~/.bashrc')
        print('  or restart your terminal.')
    else:
      print('  Error: installation failed.')
      exit(-1)

if __name__ == '__main__':
  installer = Installer()
  installer.run()