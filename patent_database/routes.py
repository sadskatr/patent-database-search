from flask import render_template, jsonify, request, current_app, send_file
from . import patent_database_bp
from .operations import run_operation, search_patents, export_to_csv
from .constants import SEARCH_TYPES, VALID_FIELDS, FIELD_DISPLAY_NAMES, BOOLEAN_OPERATORS, API_ENDPOINTS
import logging
import json
import io
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@patent_database_bp.route('/')
def index():
    """Render the main index page"""
    return render_template('patent_database/index.html', 
                           tool_name=current_app.config.get('TOOL_NAME', 'Patent Search Tool'),
                           search_types=SEARCH_TYPES,
                           valid_fields=VALID_FIELDS,
                           field_display_names=FIELD_DISPLAY_NAMES,
                           boolean_operators=BOOLEAN_OPERATORS,
                           max_results=current_app.config.get('MAX_RESULTS_PER_PAGE', 100))

@patent_database_bp.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for patent search"""
    try:
        data = request.get_json()
        logger.info(f"Search request received: {json.dumps(data, indent=2)}")
        
        result = search_patents(data)
        
        # Log search results summary
        if result.get('success'):
            result_count = len(result.get('data', {}).get('results', []))
            total_count = result.get('data', {}).get('metadata', {}).get('total', 0)
            logger.info(f"Search returned {result_count} of {total_count} total results")
        else:
            logger.error(f"Search failed: {result.get('error')}")
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Exception in search API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@patent_database_bp.route('/api/export-csv', methods=['POST'])
def api_export_csv():
    """API endpoint to export search results to CSV"""
    try:
        data = request.get_json()
        logger.info("CSV export request received")
        
        result = export_to_csv(data)
        
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        # Create an in-memory file-like object
        buffer = io.StringIO(result.get('csv_data', ''))
        
        # Set headers for file download
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"patent_search_results_{now}.csv"
        
        return send_file(buffer, 
                        as_attachment=True,
                        download_name=filename,
                        mimetype='text/csv')
    except Exception as e:
        logger.exception(f"Exception in export CSV API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@patent_database_bp.route('/api/valid-fields/<search_type>')
def api_valid_fields(search_type):
    """API endpoint to get valid fields for a search type"""
    if search_type in VALID_FIELDS:
        fields = VALID_FIELDS[search_type]
        result = [{'field': field, 'display_name': FIELD_DISPLAY_NAMES.get(field, field)} 
                  for field in fields]
        return jsonify({'success': True, 'fields': result})
    else:
        return jsonify({'success': False, 'error': f"Invalid search type: {search_type}"}), 400

@patent_database_bp.route('/api/preview-query', methods=['POST'])
def api_preview_query():
    """API endpoint to preview the constructed query without executing it"""
    try:
        from .operations import construct_query_payload, get_api_key
        data = request.get_json()
        
        # Validate the parameters
        from .utils import validate_search_params
        validated_params = validate_search_params(data)
        
        # Construct the query payload
        query_payload = construct_query_payload(validated_params)
        
        # Get the API key (masked for security)
        api_key = get_api_key()
        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '****'
        
        # Get the endpoint URL
        endpoint_url = API_ENDPOINTS['patent_search']
        
        # Create a preview object with complete details
        preview_data = {
            'endpoint_url': endpoint_url,
            'headers': {
                'X-API-KEY': masked_key,
                'Content-Type': 'application/json'
            },
            'method': 'POST',
            'query_payload': query_payload
        }
        
        return jsonify({
            'success': True,
            'preview_data': preview_data
        })
    except Exception as e:
        logger.exception(f"Exception in preview query API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@patent_database_bp.route('/api/test-connection', methods=['GET'])
def api_test_connection():
    """API endpoint to test the USPTO API connection"""
    try:
        result = run_operation({
            'operation_type': 'test_api_connection'
        })
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Exception in test connection API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500