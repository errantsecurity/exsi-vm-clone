#!/usr/bin/env python
import argparse
from pathlib import Path
import logging
import sys
import os
import shutil
import re
import subprocess

# Iterator for the values in a vmx file
def read_vmx(filename):
    with open(filename) as f:
        for line in f:
            line = line.strip()
            k = line.split('=')[0].strip()
            v = ''.join(line.split('=')[1:]).strip()[1:-1]
            yield (k, v)

# Clone a VMDK using vmkfstools
def clone_vmdk(src, dst):
    command = [
        "vmkfstools",
        "-i", src, dst,
        "-d", "thin"
    ]
    p = subprocess.check_output(command)

    
# Create the argument parser
parser = argparse.ArgumentParser(description='ESXi VM Clone Script')
parser.add_argument('source', type=str, default='bigdata/base-guac-workstation', help='the vm to clone ([datastore]/[vm-name])')
parser.add_argument('destination', type=str, help='the new vm to create ([datastore]/[vm-name])')
parser.add_argument('--volumes', '-v', type=str, default='/vmfs/volumes', help='the directory that holds your datastores (default: /vmfs/volumes)')
# Parse the arguments
args = parser.parse_args()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Build the source and destination paths from the args
source_name = args.source.split('/')[1]
dest_name = args.destination.split('/')[1]
source_path = '{0}/{1}'.format(args.volumes, args.source)
dest_path = '{0}/{1}'.format(args.volumes, args.destination)

# Make sure the given volumes directory exists
if not Path(args.volumes).exists():
    logging.error('%s: volumes directory does not exist', args.volumes)
    sys.exit(1)

# Make sure the source exists
if not Path(source_path).exists() or \
    not Path('{0}/{1}.vmx'.format(source_path, source_name)).exists():
    logging.error('%s: vm does not exist', args.source)
    sys.exit(1)

# Make sure the destination doesn't exist
if Path(dest_path).exists():
    logging.error('%s: vm already exists', args.destination)
    sys.exit(1)

# Create the directory structure for the destination
logging.info('creating destination structure')
os.makedirs(dest_path)

# Copy the VMX file and replace the references to the old name
logging.info('copying vmx configuration')
with open('{0}/{1}.vmx'.format(dest_path, dest_name), 'w') as output:
    for (key, srcval) in read_vmx('{0}/{1}.vmx'.format(source_path, source_name)):
        dstval = srcval.replace(source_name, dest_name)
        if key == 'nvram':
            logging.info('copying nvram')
            shutil.copy('{0}/{1}'.format(source_path, srcval),
                        '{0}/{1}'.format(dest_path, dstval))
        elif re.match('scsi[0-9]*:[0-9]*\\.fileName', key) != None:
            logging.info('cloning %s (%s)', key.split('.filename')[0],
                            srcval)
            clone_vmdk('{0}/{1}'.format(source_path, srcval),
                        '{0}/{1}'.format(dest_path, dstval)
            )
        elif key == 'sched.swap.derivedName':
            logging.info('copying swap file')
            try:
                shutil.copy(srcval, dstval)
            except FileNotFoundError:
                logging.warning('swap file does not exist.')
                pass
        # Write the config to the new VM
        output.write('{0} = "{1}"\n'.format(key, dstval))

logging.info('registering vm in esxi')
subprocess.check_output(['vim-cmd', 'solo/registervm', '{0}/{1}.vmx'.format(dest_path, dest_name)])
