#!/usr/bin/env bash

MODULE_PATHS=$@
SOURCE_DIR=docs/source
BUILD_DIR=docs/build


for MODULE_PATH in $MODULE_PATHS
do
# Generate source files from module path
sphinx-apidoc -f -o $SOURCE_DIR $MODULE_PATH
done

# Replace delimiter
SOURCE_FILES=${MODULE_PATHS/ /\\n   }

# Insert source file name
sed "s/Contents:/Contents:\n\n   $SOURCE_FILES/g" $SOURCE_DIR/index.tmpl.rst > $SOURCE_DIR/index.rst

# Generate html documentation from source files
sphinx-build -b html $SOURCE_DIR $BUILD_DIR