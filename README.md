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

## Caveats
For this to work there are a few minor things to keep in mind:
1. The 1Password CLI has no way of filtering items by category "SSH-Keys".  
   So, as a workaround, all your keys need to have a tag "SSH-Key" or "SSH-Keys"
2. In order to write a proper config file for ssh every SSH-Key needs a URL-field labelled "URL".  
   This field must contain the URL that is used to log in via SSH