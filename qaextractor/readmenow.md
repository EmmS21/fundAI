dagger call run \
  --mongodb-uri env:MONGODB_URI \
  --credentials-json env:GOOGLE_CREDENTIALS \
  --source-dir . \
  --process-all

export MONGODB_URI="mongodb+srv://EmmSibs21:Kaleidoscope69@adalchemyai.q3tzkok.mongodb.net/?retryWrites=true&w=majority&appName=AdAlchemyAI"

export DAGGER_CLOUD_TOKEN="ddb57cb7-2be9-49cc-8876-39b116de0b13"                                                                            
export GOOGLE_CREDENTIALS=$(cat /Users/ripplingadmin/Documents/GitHub/fundAI/qaextractor/extract/credentials.json)

Run Answers sheet
dagger call single --credentials-json=env:GOOGLE_CREDENTIALS --file-id="1sxDchOhHELdbu8soFSKZm6M51oFNDZ1F" --document-type="answers"