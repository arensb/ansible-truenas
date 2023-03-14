RM = rm -rf

all::

# Build a tarball that can be uploaded as an Ansible collection.
tarball:
	ansible-galaxy collection build --force

clean::
	${RM} arensb-truenas-*.tar.gz
