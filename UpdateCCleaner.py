import requests
import subprocess
import os
import re
import sys


VERSION_STRING = re.compile('(?:[0-9]+\.*?){3}')
BASE_DIR = os.environ['ProgramFiles']  # ProgramFiles(x86)


class Version:
    def __init__(self, major, minor, build):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)

    def __gt__(self, other):
        return isinstance(other, Version) and \
            (self.build > other.build or self.minor > other.minor or self.major > other.major)

    def __str__(self):
        return '%d.%d.%d' % (self.major, self.minor, self.build)


def detect_install():
    full_path = os.path.join(BASE_DIR, 'CCleaner')
    exe_path = os.path.join(full_path, 'CCleaner.exe')

    if os.path.exists(full_path) and os.path.exists(exe_path):
        return exe_path

    return None


def get_local_version(exe_path=''):
    if exe_path == '':
        exe_path = detect_install()

    if exe_path is None or exe_path == '':
        print('Invalid exe path, unable to auto-detect.')
        exit()

    escaped_path = exe_path.replace('\\', '\\\\')  # Hmm
    code, out = subprocess.getstatusoutput('wmic DATAFILE WHERE NAME="%s" GET version' % escaped_path)

    if code != 0:
        print('Invalid code when checking CCleaner version:', code)
        exit()

    version = out.strip().split('\n')[-1].split('.')

    if len(version) == 4:
        major, minor, build = [version[0], version[1], version[3]]
    elif len(version) == 3:
        major, minor, build = version
    else:
        print('Unexpected version schema. Expected 3-4 values, got %d' % len(version))

    return Version(major, minor, build)


def download_latest(filename, url):
    res = requests.get(url, stream=True)

    def report_progress(cur, tot):
        bar_len = 32
        progress = float(cur) / tot
        filled_len = int(round(bar_len * progress))
        percent = round(progress * 100, 2)

        bar = '█' * filled_len + ' ' * (bar_len - filled_len)
        sys.stdout.write('Downloading latest version |%s| %0.2f%% (%d/%d)\r' % (bar, percent, cur, tot))
        sys.stdout.flush()

        if cur >= tot:
            sys.stdout.write('\n')

    def read_chunk(f, chunk_size=8192):
        total_bytes = int(res.headers['Content-Length'].strip())
        current_bytes = 0

        for chunk in res.iter_content(chunk_size):
            f.write(chunk)
            current_bytes += len(chunk)
            report_progress(current_bytes, total_bytes)

    with open(filename, 'wb') as f:
        read_chunk(f)

    install_latest(filename)


def install_latest(filename):
    print('Installing...')

    code, out = subprocess.getstatusoutput('%s /S' % filename)

    if code == 0:
        print('CCleaner successfully updated!')
        os.remove(filename)
        exit()
    else:
        print('Update failed!\n%s' % out)
        exit()


def check_latest():
    current_version = get_local_version()

    res = requests.get('https://ccleaner.com/auto?a=3&p=cc&v=%s' % current_version)
    new_ver = VERSION_STRING.search(res.text)

    if new_ver is None:
        print('Unable to find new version!')
        exit()

    major, minor, build = new_ver.group().split('.')
    latest_version = Version(major, minor, build)

    if latest_version > current_version:
        print('Update available\n  New version: %s\n  Current version: %s' % (latest_version, current_version))
        filename = 'ccsetup%d%d.exe' % (latest_version.major, latest_version.minor)
        download_url = 'https://download.ccleaner.com/%s' % filename
        download_latest(filename, download_url)
    else:
        print('You are running the latest version!')
        exit()


if __name__ == '__main__':
    try:
        check_latest()
    except KeyboardInterrupt:
        pass
