import json
import os
import re
import subprocess
import sys
from pathlib import Path


class SSHKeyImporter():
    """Uses the 1Password command line interface to load ssh keys and export the public keys to the file system.
    Only keys with at least one of the tags defined in TAGS are imported.
    The importer will make use of additional fields if they are labelled as follows:
    - URL: Will be used as the HostName of the SSH Server
    - User: Will be used as the default user to log into the SSH Server
    - Labels: Will be used as alias for the SSH Command"""
    HOME_DIR = str(Path.home())
    SSH_CONFIG_DIR = os.path.join(HOME_DIR, '.ssh')
    EXPORT_PUBKEY_DIR = os.path.join(SSH_CONFIG_DIR, '1password')

    TAGS = 'SSH-Key,SSH-Keys'

    def __init__(self, useraction='prompt', urlaction='prompt', labelsaction='prompt'):
        self.useraction = useraction
        self.urlaction = urlaction
        self.labelsaction = labelsaction

        if sys.platform.startswith('linux'):
            self.identityAgent = '~/.1password/agent.sock'
        elif sys.platform.startswith('darwin'):
            self.identityAgent = '"~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"'
        else:
            self.identityAgent = None

    def startImport(self):
        """Loads SSH keys from 1Password, exports the public keys and writes the ssh config file"""
        self.getKeyList()
        self.exportKeys()
        self.writeHostFile()

    def getKeyList(self):
        """Loads the SSH key list"""
        print('Loading SSH Keys from 1Password')
        try:
            jsonData = subprocess.check_output(f'op item list --vault=Personal --tags={self.TAGS} --format=json', shell=True)
        except subprocess.CalledProcessError:
            print('ERROR: Couldn\'t load SSH keys from 1Password')
            sys.exit(1)
        self.keys = json.loads(jsonData)
        for key in self.keys:
            try:
                key.update(self._getPublicKey(key))
            except subprocess.CalledProcessError:
                continue
            self.handleMissingFields(key)
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

    def handleMissingFields(self, key):
        """Checks if all required fields are set and prompts them if not"""
        if not key.get('url'):
            if self.urlaction == 'prompt':
                print('  - Key has no URL. You can provide it now.')
                key['url'] = input('  >>> ')
            else:
                key['url'] = ''

            if key['url']:
                key['updated_fields'] = ['url']
        if not key.get('user'):
            if self.useraction == 'prompt':
                print('  - Key has no Username. You can provide it now.')
                key['user'] = input('  >>> ')
            elif self.useraction == 'leave-empty':
                key['user'] = ''
            else:
                key['user'] = self.useraction

            if key['user']:
                key['updated_fields'] = key.get('updated_fields', []) + ['user']
        if not key.get('labels'):
            defaults = [self._getShortTitle(key), key['url']]
            if self.labelsaction == 'prompt':
                print(f'  - Key has no labels. You can provide them now. (Leave empty for default "{self._getShortTitle(key)}", "{key["url"]}")')
                key['labels'] = self._splitLabels(input('  >>> ')) or defaults
            else:
                key['labels'] = defaults

            if key['labels']:
                key['updated_fields'] = key.get('updated_fields', []) + ['labels']
        else:
            key['labels'] = self._splitLabels(key['labels'])


    def writeHostFile(self):
        """Writes a ssh config file with all valid hosts/keys that can be included in ~/.ssh/config"""
        hosts = [(
            '# This file was created by the 1Password SSH-Key importer (updateSSH.py)',
            '# Manual changes to this file will be overwritten by the script'
        )]
        for key in self.keys:
            hosts.append([f'Host {" ".join(key["labels"])}'])
            if key['url']:
                hosts[-1].append(f'  HostName {key["url"]}')
            if 'public key' in key:
                hosts[-1].append(f'  IdentityFile {key["fileName"]}')
                hosts[-1].append('  IdentitiesOnly yes')
            if key['user']:
                hosts[-1].append(f'  User {key["user"]}')
            if self.identityAgent:
                hosts[-1].append(f'  IdentityAgent {self.identityAgent}')

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
        keyData = subprocess.check_output(f'op item get {key["id"]} --format=JSON', shell=True)
        print(f'Loaded {key["title"]!r}')
        return {entry['label'].lower(): entry.get('value') for entry in json.loads(keyData)['fields']}

    def _getShortTitle(self, key):
        return re.sub(r'(ssh(\-key)?)|[^a-z0-9]+', '', key['title'].lower())

    def _splitLabels(self, labels):
        return [label for label in labels.replace(' ', ',').split(',') if label]


if __name__ == '__main__':
    if '--help' in sys.argv:
        print(re.sub(r'\n\s+', '\n', SSHKeyImporter.__doc__))
        print('Usage: python3 updateSSH.py')
        print('Args:')
        print('  --if-user-empty={prompt|leave-empty|<default_value>}')
        print('    Defines the behaviour if a key has no field labelled "User"')
        print('    - prompt: Will prompt for a user name (default)')
        print('    - leave-empty: Will not set a User in the config file')
        print('    - <default_value>: Will use the provided value as User')
        print('  --if-url-empty={prompt|leave-empty}')
        print('    Defines the behaviour if a key has no field labelled "URL"')
        print('    - prompt: Will prompt for a url (default)')
        print('    - leave-empty: Will not set a HostName in the config file')
        print('  --if-labels-empty={prompt|use-default}')
        print('    Defines the behaviour if a key has no field labelled "Labels"')
        print('    - use-default: Will use the URL and a short name that is generated from the keys title as default (default)')
        print('    - prompt: Will prompt for labels')
        sys.exit(0)

    useraction = 'prompt'
    urlaction = 'prompt'
    labelsaction = 'use-default'
    for arg in sys.argv[1:]:
        if arg.startswith('--if-user-empty='):
            useraction = arg.replace('--if-user-empty=', '')
        elif arg.startswith('--if-url-empty='):
            urlaction = arg.replace('--if-url-empty=', '')
            if urlaction not in (allowed := ('prompt', 'leave-empty')):
                print('Invalid value for argument "--if-url-empty":', urlaction)
                print('Allowed values:', ", ".join(allowed))
                sys.exit(1)
        elif arg.startswith('--if-labels-empty='):
            labelsaction = arg.replace('--if-labels-empty=', '')
            if labelsaction not in (allowed := ('prompt', 'use-default')):
                print('Invalid value for argument "--if-labels-empty":', labelsaction)
                print('Allowed values:', ", ".join(allowed))
                sys.exit(1)
        else:
            print(f'Error: Unknown argument: "{arg}"')
            sys.exit(1)

    importer = SSHKeyImporter(useraction, urlaction, labelsaction)
    importer.startImport()
