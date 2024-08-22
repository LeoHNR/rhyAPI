import json
import logging

from fastapi import  HTTPException, Depends

from utils.database import fetch_query_as_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_cards():
    query = "SELECT * FROM dbo.cards"
    try:
        logger.info("QUERY LIST")
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))