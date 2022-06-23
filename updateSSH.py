import json
import os
import re
import subprocess
import sys
from pathlib import Path


class SSHKeyImporter():
    """Uses the 1Password command line interface to load ssh keys and export the public keys to the file system.
    Only keys with at least one of the tags defined in TAGS are imported.
    Additionally, every SSH-Key needs a field labelled "URL" in order to be imported"""
    HOME_DIR = str(Path.home())
    SSH_CONFIG_DIR = os.path.join(HOME_DIR, '.ssh')
    EXPORT_PUBKEY_DIR = os.path.join(SSH_CONFIG_DIR, '1password')

    TAGS = 'SSH-Key,SSH-Keys'

    def __init__(self, user=None):
        self.user = user or None

    def startImport(self):
        """Loads SSH keys from 1Password, exports the public keys and writes the ssh config file"""
        self.getKeyList()
        self.exportKeys()
        self.writeHostFile()

    def getKeyList(self):
        """Loads the SSH key list"""
        print('Loading SSH Keys from 1Password')
        jsonData = subprocess.check_output(f'op item list --vault=Personal --tags={self.TAGS} --format=json', shell=True)
        self.keys = json.loads(jsonData)
        for key in self.keys:
            try:
                key.update(self._getPublicKey(key))
            except subprocess.CalledProcessError:
                continue
        print()

    def exportKeys(self):
        """Exports all loaded public keys to EXPORT_PUBKEY_DIR"""
        if not os.path.exists(self.EXPORT_PUBKEY_DIR):
            os.mkdir(self.EXPORT_PUBKEY_DIR)

        for key in self.keys:
            if 'public key' in key:
                key['fileName'] = os.path.join(self.EXPORT_PUBKEY_DIR, self._getShortTitle(key)) + '.pub'
                print(f'Exporting {key["title"]!r} to {key["fileName"]!r}')
                with open(key['fileName'], 'w') as f:
                    f.write(key['public key'])
        print()

    def writeHostFile(self):
        """Writes a ssh config file with all valid hosts/keys that can be included in ~/.ssh/config"""
        hosts = [(
            '# This file was created by the 1Password SSH-Key importer (SSHImport.py)',
            '# Manual changes to this file will be overwritten by the script'
        )]
        for key in self.keys:
            hosts.append([f'Host {self._getShortTitle(key)}'])
            if 'URL' in key:
                hosts[-1].append(f'  HostName {key["URL"]}')
            if 'public key' in key:
                hosts[-1].append(f'  IdentityFile {key["fileName"]}')
                hosts[-1].append('  IdentitiesOnly yes')
            if self.user:
                hosts[-1].append(f'  User {self.user}')

        fileName = os.path.join(self.EXPORT_PUBKEY_DIR, 'config')
        with open(fileName, 'w') as f:
            print('Writing config file:', fileName)
            for host in hosts:
                if len(host) == 1:
                    continue
                f.write('\n'.join(host))
                f.write('\n\n')
        print('\nDone. Please make sure that your "~/.ssh/config" file starts with the following line:')
        print('Include ', fileName)

    def _getPublicKey(self, key):
        """Loads URL and public key for a given item id"""
        keyData = subprocess.check_output(f'op item get {key["id"]} --fields label=URL,label="public key" --format=JSON', shell=True)
        print(f'Loaded {key["title"]!r}')
        return {entry['label']: entry['value'] for entry in json.loads(keyData)}

    def _getShortTitle(self, key):
        return re.sub(r'(ssh(\-key)?)|[^a-z]+', '', key['title'].lower())


if __name__ == '__main__':
    user = None
    for arg in sys.argv:
        if arg.startswith('--user='):
            user = arg.replace('--user=', '')

    if not user:
        print('Please provide the user name that is used to log into ssh. (Press enter to leave empty)')
        user = input('>>> ')
        print()

    importer = SSHKeyImporter(user=user)
    importer.startImport()
