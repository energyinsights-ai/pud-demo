from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import logging
import traceback
import sys
load_dotenv()

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "https://your-frontend-domain.herokuapp.com",  # Replace with your actual frontend domain
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.before_request
def log_request_info():
    logger.info('Headers: %s', request.headers)
    logger.info('Body: %s', request.get_data())
    logger.info('URL: %s', request.url)

def get_db_connection():
    load_dotenv()

    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')

    )
    return conn


@app.route('/tr')
def get_tr_data():
    try:
        conn = get_db_connection()
        print(conn.get_dsn_parameters())
        cur = conn.cursor()
        
        # Check if the table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'demo' 
                AND table_name = 'tr'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        if not table_exists:
            logger.error("Table demo.tr does not exist")
            return jsonify({
                "error": "Table not found",
                "message": "The required table does not exist"
            }), 404
            
        cur.close()
        
        # If table exists, proceed with the main query
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT jsonb_build_object(
                    'type',     'FeatureCollection',
                    'features', COALESCE(jsonb_agg(feature), '[]'::jsonb)
                ) as geojson
                FROM (
                    SELECT jsonb_build_object(
                        'type',       'Feature',
                        'geometry',   ST_AsGeoJSON(geom)::jsonb,
                        'properties', jsonb_build_object(
                            'id', id,
                            'basin', basin,
                            'state', state,
                            'tr', tr
                        )
                    ) AS feature
                    FROM demo.tr
                    WHERE basin = 'DJ'
                ) features;
            """)
            
            result = cur.fetchone()
            
            if result and result['geojson']:
                return jsonify(result['geojson'])
                
            return jsonify({
                "type": "FeatureCollection",
                "features": []
            })
            
        except Exception as query_error:
            logger.error(f"Query execution error: {str(query_error)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    except psycopg2.Error as e:
        logger.error(f"Database error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/wells/<tr_id>')
def get_wells_by_tr(tr_id):
    try:
        radius = request.args.get('radius', default=10, type=float)
        logger.info(f"Received request for TR {tr_id} with radius {radius} miles")
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # First get the centroid for the selected TR
        cur.execute("""
            SELECT ST_X(centroid) as lon, ST_Y(centroid) as lat 
            FROM demo.tr 
            WHERE tr = %s AND basin = 'DJ'
        """, (tr_id,))
        
        tr_point = cur.fetchone()
        if not tr_point:
            return jsonify({
                "error": "TR not found",
                "message": f"Could not find TR {tr_id}"
            }), 404
            
        # Log the query parameters
        logger.info(f"Querying wells around point ({tr_point['lon']}, {tr_point['lat']}) with {radius} mile radius")
        
        # Get wells within radius
        cur.execute("""
            SELECT 
                w.well_id,
                w.api_14,
                w.well_name,
                w.env_operator,
                w.interval,
                w.spud_date,
                w.lateral_length,
                ST_AsGeoJSON(w.geom)::json as geometry
            FROM demo.wells w
            WHERE w.geom IS NOT NULL
                AND ST_DistanceSphere(
                    w.geom, 
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                ) <= %s * 1609.34
                AND w.spud_date > '2010-01-01'::date
            ORDER BY w.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        """, (tr_point['lon'], tr_point['lat'], radius, tr_point['lon'], tr_point['lat']))
        
        wells = cur.fetchall()
        logger.info(f"Found {len(wells)} wells within {radius} miles of TR {tr_id}")
        
        # Debug: Log first few wells
        if wells:
            logger.info("Sample wells:")
            for well in wells[:3]:
                logger.info(f"API: {well['api_14']}, Name: {well['well_name']}")
        
        return jsonify({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": well['geometry'],
                "properties": {
                    k: v for k, v in well.items() if k != 'geometry'
                }
            } for well in wells]
        })
        
    except Exception as e:
        logger.error(f"Error fetching wells: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/wells/<api_14>/production')
def get_well_production(api_14):
    logger.info(f"=== Starting production request for API: {api_14} ===")
    try:
        conn = get_db_connection()
        logger.info("Database connection established")
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Debug query to see what's in the wells table
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM demo.wells
        """)
        total_wells = cur.fetchone()
        logger.info(f"Total wells in database: {total_wells['count']}")
        
        # First verify the well exists
        well_query = """
            SELECT well_id, well_name 
            FROM demo.wells 
            WHERE api_14 = %s
        """
        logger.info(f"Executing well query: {well_query} with API: {api_14}")
        cur.execute(well_query, (api_14,))
        
        well = cur.fetchone()
        if not well:
            # Debug query to see similar API numbers
            cur.execute("""
                SELECT api_14, well_name 
                FROM demo.wells 
                WHERE api_14 LIKE %s
                LIMIT 5
            """, (f"{api_14[:5]}%",))
            similar_wells = cur.fetchall()
            logger.warning(f"Well not found. Similar APIs: {similar_wells}")
            
            return jsonify({
                "error": "Well not found",
                "message": f"Could not find well with API: {api_14}",
                "details": {
                    "similar_wells": similar_wells,
                    "api_searched": api_14
                }
            }), 404
        
        logger.info(f"Found well: {well['well_name']} (API: {api_14})")
        
        # Get production data with debug query
        query = """
            SELECT 
                prod_date::date,
                ROUND(oil::numeric, 2) as oil,
                ROUND(gas::numeric, 2) as gas
            FROM demo.production
            WHERE api_14 = %s
                AND oil IS NOT NULL 
                AND gas IS NOT NULL
            ORDER BY prod_date
        """
        
        logger.info(f"Executing production query: {query} with API: {api_14}")
        
        cur.execute(query, (api_14,))
        production = cur.fetchall()
        
        # Log detailed results
        logger.info(f"Query returned {len(production)} production records")
        if len(production) > 0:
            logger.info(f"Sample first record: {production[0]}")
            logger.info(f"Sample last record: {production[-1]}")
        else:
            # Check if any production exists without NULL filters
            cur.execute("""
                SELECT COUNT(*), 
                       COUNT(*) FILTER (WHERE oil IS NULL) as null_oil,
                       COUNT(*) FILTER (WHERE gas IS NULL) as null_gas
                FROM demo.production 
                WHERE api_14 = %s
            """, (api_14,))
            counts = cur.fetchone()
            logger.warning(
                f"No production found with non-null values. "
                f"Total records: {counts['count']}, "
                f"Null oil: {counts['null_oil']}, "
                f"Null gas: {counts['null_gas']}"
            )
        
        return jsonify({
            "api_14": api_14,
            "well_name": well['well_name'],
            "production": production,
            "record_count": len(production)
        })
        
    except Exception as e:
        logger.error(f"Error fetching production for API {api_14}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Server error",
            "message": str(e),
            "type": type(e).__name__,
            "api_14": api_14
        }), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/wells/aggregate-production', methods=['POST'])
def get_aggregate_production():
    try:
        # Log the incoming request
        logger.info(f"Received production request - Headers: {request.headers}")
        logger.info(f"Request data: {request.get_data()}")
        
        api_list = request.json.get('apis', [])
        if not api_list:
            logger.warning("No APIs provided in request")
            return jsonify({
                "error": "No APIs provided",
                "message": "Please provide a list of API14s"
            }), 400

        logger.info(f"Processing production for APIs: {api_list[:5]}...")  # Log first 5 APIs
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify APIs exist in the database
        cur.execute("""
            SELECT DISTINCT api_14 
            FROM demo.wells 
            WHERE api_14 = ANY(%s)
        """, (api_list,))
        found_apis = [row['api_14'] for row in cur.fetchall()]
        
        if not found_apis:
            logger.warning(f"No matching APIs found in database")
            return jsonify({
                "error": "No matching wells",
                "message": "None of the provided APIs were found in the database",
                "requested_apis": api_list
            }), 404
            
        logger.info(f"Found {len(found_apis)} matching wells in database")

        # Query to get individual well production data normalized by months
        query = """
            WITH first_prod AS (
                SELECT 
                    api_14,
                    MIN(prod_date) as first_prod_date
                FROM demo.production
                WHERE api_14 = ANY(%s)
                GROUP BY api_14
            ),
            monthly_prod AS (
                SELECT 
                    p.api_14,
                    EXTRACT(YEAR FROM age(p.prod_date::date, fp.first_prod_date::date)) * 12 +
                    EXTRACT(MONTH FROM age(p.prod_date::date, fp.first_prod_date::date)) + 1 as month_num,
                    p.oil
                FROM demo.production p
                JOIN first_prod fp ON p.api_14 = fp.api_14
                WHERE p.oil IS NOT NULL
                    AND p.api_14 = ANY(%s)
            )
            SELECT 
                api_14,
                month_num,
                ROUND(oil::numeric, 2) as oil
            FROM monthly_prod
            WHERE month_num <= 48
            ORDER BY api_14, month_num;
        """
        
        logger.info("Executing production query...")
        cur.execute(query, (api_list, api_list))
        results = cur.fetchall()
        
        # Organize data by API
        wells_data = {}
        for row in results:
            api = row['api_14']
            if api not in wells_data:
                wells_data[api] = []
            wells_data[api].append({
                'month': row['month_num'],
                'oil': row['oil']
            })
        
        logger.info(f"Processed production data for {len(wells_data)} wells")
        # Add sample data logging
        if wells_data:
            sample_api = next(iter(wells_data))
            logger.info(f"Sample data structure for API {sample_api}:")
            logger.info(f"First 3 months: {wells_data[sample_api][:3]}")
        
        return jsonify({
            "success": True,
            "data": wells_data,
            "well_count": len(wells_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching production: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
