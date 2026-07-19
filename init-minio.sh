#!/bin/sh

#wait for the main MinIo server to boot up completely
sleep 3;

# connect the command line client (mc) to your local MinIo container
mc alias  set myminio "$MINIO_ENDPOINT" "$MINIO_USER" "$MINIO_PASSWORD";

# create the bucket if it doesnot exists
mc mb --ignore-existing myminio/"$BUCKET_NAME";

# optional: set the bucket policy to public so users can download / view images and files
mc anonymous set public myminio/"$BUCKET_NAME";

exit 0;