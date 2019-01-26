# exsi-vm-clone
Script to automatically clone and register a VM on ESXi
Usage: from esxi shell: python clone.py sourceDatastore/sourceVMname destinationDatastore/desiredVMName
Note: Script assumes the VM is powered off. We normally create a VM and then power it off and unregister it, then use it as our master copy. Great for spinning up temporary servers or boxes to throw malware at!

Thanks all
@crisco
