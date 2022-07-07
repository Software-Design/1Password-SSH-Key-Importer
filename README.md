# Load SSH-Keys from 1Password and export the public keys
## Prerequisites
### Enable unlocking the command line interface through the 1Password app
1. Open 1Password
2. Click the account or collection at the top of the sidebar and choose Developer
3. Select Biometric Unlock for 1Password CLI

### Install the 1Password cli
```bash
brew install --cask 1password/tap/1password-cli

# This command will try to log you in through the 1Password app.
# If this works, you're good to go
op vault ls
```

## Usage
Just run the script using Python3
```bash
python3 updateSSH.py
```

## How it works
1. The script will load every SSH-Key from 1Password that satisfies the following conditions:
   - They lie in your "Personal" vault
   - They are tagged with either "SSH-Key" or "SSH-Keys"
2. The public keys of these items are exported to `~/.ssh/1password/<short_title>.pub`, where the `short_title` is generated from the item's lower-case title by removing the word "ssh(-key)" and any non-letter character.  
   An SSH-Key with the title "SSH-Key MyServer" will for example be exported to "~/.ssh/1password/myserver.pub"
3. The script will look for fields labelled "User", "URL" and "Labels" in the SSH Keys. If not present, they will be prompted via command line.  
4. An SSH config file is written to `~/.ssh/1password/config` that contains a host entry for every exported SSH-Key  
   These entries look like the following
   ```
   Host <labels>
     HostName <URL>
     IdentityFile ~/.ssh/1password/<short_title>.pub
     IdentitiesOnly yes
     User <user>
   ```
   With this config you will be able to just type `ssh <short_title>` and you will be connected as the user provided in step 1

Make sure to add this line at the start of your `~/.ssh/config` file in order to include the generated config file.
```
Include ~/.ssh/1password/config
```