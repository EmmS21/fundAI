Upload

curl -X POST http://localhost:8080/upload \
  -F "file=@******.pdf" \
  -F "version=1.0.0" \
  -F "description=Linux text editor" \
  -F "app_version=2.1.0" \
  -F "app_type=editor"

