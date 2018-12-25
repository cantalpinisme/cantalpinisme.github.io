#!/bin/sh

# Copy local files to website

. ./env_sftp.sh

lftp sftp://$SFTP_USER:$SFTP_PASS@$SFTP_HOST -e "mirror -e -R $PWD/build/ $SFTP_ROOT ; quit"
