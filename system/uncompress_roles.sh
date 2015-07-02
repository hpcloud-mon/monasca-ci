#!/bin/bash
# Uncompress the tarball artifacts for ansible roles stripping the ansible- in the role name
# This works in conjunction with the jjb macro uncompress-roles which in turn works with artifact copying from Ansible lint jobs
base_dir=$PWD
target_dir=$1
for file in `ls artifacts/tars/*.tar.gz`; do
  full_name=`basename $file`
  file_name=${full_name%.tar.gz}
  role_name=${file_name#ansible-}
  mkdir -p $target_dir/$role_name
  cd $target_dir/$role_name
  tar -xzf $base_dir/$file
  cd $base_dir
done
