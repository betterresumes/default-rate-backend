import json
import os

def merge_collections():
    """
    Merges multiple Postman collection JSON files into a single collection.
    """
    collection_parts = [
        "POSTMAN_COLLECTION_PART_1_AUTH_USER.json",
        "POSTMAN_COLLECTION_PART_2_BIZ_OPS.json",
        "POSTMAN_COLLECTION_PART_3_PREDICTIONS.json"
    ]
    
    final_collection = None
    
    for part_file in collection_parts:
        if not os.path.exists(part_file):
            print(f"Warning: Collection part '{part_file}' not found. Skipping.")
            continue
            
        with open(part_file, 'r') as f:
            part_data = json.load(f)
            
        if final_collection is None:
            # Initialize with the first part
            final_collection = part_data
        else:
            # Merge items (folders) from subsequent parts
            if "item" in part_data:
                final_collection["item"].extend(part_data["item"])

    if final_collection:
        # Update the final collection's name
        final_collection["info"]["name"] = "Complete API Collection"
        final_collection["info"]["description"] = "This is the complete, merged Postman collection for all application APIs."
        
        output_filename = "COMPLETE_POSTMAN_COLLECTION_FINAL.json"
        with open(output_filename, 'w') as f:
            json.dump(final_collection, f, indent=2)
            
        print(f"Successfully merged collections into '{output_filename}'")
    else:
        print("No collection parts were found to merge.")

if __name__ == "__main__":
    merge_collections()
