#!/usr/bin/env bash
# Install SSM globally on Ubuntu

# Make launcher executable
chmod +x ssm

# Copy launcher to /usr/local/bin so it can be run anywhere
sudo cp ssm /usr/local/bin/ssm

echo "SSM installed globally!"
echo "You can now run 'ssm' from any terminal."
