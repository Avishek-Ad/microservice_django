import pymongo
from django.conf import settings

url = settings.MONGODB_URL

try:
    client = pymongo.MongoClient(url)
    
    db = client['django_mongo_db'] # if this db doesnot exist mongo will create it on first write operation
    
    client.admin.command('ping')
    print("[SUCCESS] Connected to MongoDB container successfully!")
except Exception as e:
    print(f"[ERROR] Mongo db connection failed with error : {str(e)}")