from flask import Flask, request, jsonify

app = Flask(__name__)

# Sample data storage (in-memory)
items = [
    {"id": 1, "name": "Item 1", "description": "First item"},
    {"id": 2, "name": "Item 2", "description": "Second item"}
]


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Flask API",
        "endpoints": [
            "/",
            "/health",
            "/api/items",
            "/api/items/<item_id>"
        ]
    }), 200

# GET - Retrieve all items
@app.route('/api/items', methods=['GET'])
def get_items():
    return jsonify(items), 200

# GET - Retrieve a specific item by ID
@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = next((i for i in items if i["id"] == item_id), None)
    if item:
        return jsonify(item), 200
    return jsonify({"error": "Item not found"}), 404

# POST - Create a new item
@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Name is required"}), 400
    
    new_item = {
        "id": max([i["id"] for i in items]) + 1 if items else 1,
        "name": data.get("name"),
        "description": data.get("description", "")
    }
    items.append(new_item)
    return jsonify(new_item), 201

# PUT - Update an existing item
@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    data = request.get_json()
    item["name"] = data.get("name", item["name"])
    item["description"] = data.get("description", item["description"])
    return jsonify(item), 200

# DELETE - Remove an item
@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    global items
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    items = [i for i in items if i["id"] != item_id]
    return jsonify({"message": "Item deleted"}), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
