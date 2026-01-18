from elasticsearch import Elasticsearch
from config import Config

# Initialize Elasticsearch client
es_client = Elasticsearch([Config.ELASTICSEARCH_URL])

def index_torrent(torrent):
    try:
        doc = {
            "id": torrent.id,
            "info_hash": torrent.info_hash,
            "filename": torrent.filename,
            "description": torrent.description,
            "file_size": torrent.file_size,
            "piece_length": torrent.piece_length,
            "seeders": torrent.seeders,
            "leechers": torrent.leechers,
            "completed": torrent.completed,
            "uploader_id": torrent.uploader_id,
            "created_at": torrent.created_at.isoformat(),
            "updated_at": torrent.updated_at.isoformat()
        }

        es_client.index(index="torrents", id=torrent.id, body=doc)
        return True
    except Exception as e:
        print(f"Failed to index torrent {torrent.id}: {e}")
        return False

def search_torrents_elasticsearch(query: str, limit: int = 50):
    """
    Search for torrents in Elasticsearch by filename, description, or info_hash.

    Args:
        query (str): Search string
        limit (int): Maximum number of results to return

    Returns:
        List of torrent results or empty list if no matches
    """
    try:
        search_body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["filename^3", "description^2", "info_hash"],
                    "fuzziness": "AUTO"
                }
            }
        }

        response = es_client.search(index="torrents", body=search_body)

        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            results.append({
                "id": source.get('id'),
                "filename": source.get('filename'),
                "description": source.get('description'),
                "info_hash": source.get('info_hash'),
                "file_size": source.get('file_size'),
                "seeders": source.get('seeders'),
                "leechers": source.get('leechers'),
                "completed": source.get('completed'),
                "created_at": source.get('created_at'),
                "score": round(hit['_score'], 2)
            })

        return results
    except Exception as e:
        print(f"Elasticsearch search error: {e}")
        return []

def delete_torrent_index(torrent_id):
    """Delete a torrent from Elasticsearch index."""
    try:
        es_client.delete(index="torrents", id=torrent_id)
        return True
    except Exception as e:
        print(f"Failed to delete torrent {torrent_id} from index: {e}")
        return False

def update_torrent_swarm_info(torrent_id, seeders: int, leechers: int, completed: int = None):
    """Update swarm information for a torrent."""
    try:
        update_body = {
            "doc": {
                "seeders": seeders,
                "leechers": leechers
            }
        }

        if completed is not None:
            update_body["doc"]["completed"] = completed

        es_client.update(index="torrents", id=torrent_id, body=update_body)
        return True
    except Exception as e:
        print(f"Failed to update swarm info for torrent {torrent_id}: {e}")
        return False