from datetime import datetime
from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class DatabaseConnection:
    _client = None
    _db = None

    @classmethod
    def connect(cls):
        if cls._client is None:
            try:
                uri = os.getenv('URI')
                cls._client = MongoClient(uri,server_api=ServerApi('1'))
                cls._db = cls._client['notion-automations']
                logger.info("Conexión establecida a la base de datos.")
            except errors.ConnectionFailure as e:
                logger.error(f"Error de conexión a la base de datos: {e}")
                raise
    
    @classmethod
    def create_document(cls, collection_name, document, hasDate = False):
        """Crear un nuevo documento en la colección."""
        collection = cls.get_collection(collection_name)
        try:
            result = collection.insert_one(document)
            document['_id'] = document['_id'].binary.hex()
            if hasDate:
                document['timestamp'] = document['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Documento creado con ID: {result.inserted_id}")
            return document['_id']
        except errors.PyMongoError as e:
            logger.error(f"Error al crear el documento: {e}")
            raise

    @classmethod
    def close_connection(cls):
        """Cerrar la conexión a la base de datos."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("Conexión a la base de datos cerrada.")

    @classmethod
    def is_valid_objectid(cls, id: str) -> bool:
        try:
            ObjectId(id)
            return True
        except Exception:
            return False

if __name__ == '__main__':
    DatabaseConnection.connect()
    DatabaseConnection.close_connection()