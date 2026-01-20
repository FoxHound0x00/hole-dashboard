from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
import collections
import json
import os
import numpy as np
import pickle
import joblib
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return "Null"

@app.get("/config")
def config():
    with open("data/ph_data_all_syn.json", "r") as f:
        syn_data = json.load(f)

    with open("src/config.json", "r") as file:
        config_data = json.load(file)
        config_data["Distance Metric"] = list(syn_data.keys())
        return config_data
            
@app.get("/data/{metric}")
async def get_data(metric: str):
    with open("data/ph_data_all_syn.json", "r") as f:
        syn_data = json.load(f)
    if metric in syn_data:
        return syn_data[metric]
    
    return {}
    
    
@app.get("/cluster_data/{metric}")
async def get_cluster_data(metric: str):
    with open("data/ph_data_all_syn.json", "r") as f:
        syn_data = json.load(f)
    if metric in syn_data:
        cluster_data = {}
        for key in syn_data[metric].keys():
            cluster_data[key] = collections.Counter(syn_data[metric][key])
        return cluster_data
    
    return {}

@app.get("/distance_matrix/{metric}")
async def get_distance_matrix(metric: str):
    try:
        # Load distance matrix from .npy file
        npy_path = f"data/dist_{metric}.npy"
        if os.path.exists(npy_path):
            dist_matrix = np.load(npy_path)
            return {"matrix": dist_matrix.tolist()}
        return {"error": f"Distance matrix not found for metric: {metric}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/pca")
async def get_pca():
    try:
        # Load PCA projection from .npy file
        pca_path = "data/pca.npy"
        if os.path.exists(pca_path):
            pca_projection = np.load(pca_path)
            
            # Also load the true labels for visualization
            with open("data/point_cloud_data.json", "r") as f:
                point_data = json.load(f)
                labels = point_data["true_labels"]
            
            return {
                "projection": pca_projection.tolist(),
                "labels": labels
            }
        return {"error": "PCA projection not found"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/tsne")
async def get_tsne():
    try:
        # Load t-SNE projection from .npy file
        tsne_path = "data/tsne.npy"
        if os.path.exists(tsne_path):
            tsne_projection = np.load(tsne_path)
            
            # Also load the true labels for visualization
            with open("data/point_cloud_data.json", "r") as f:
                point_data = json.load(f)
                labels = point_data["true_labels"]
            
            return {
                "projection": tsne_projection.tolist(),
                "labels": labels
            }
        return {"error": "t-SNE projection not found"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/mds")
async def get_mds():
    try:
        # Load MDS projection from .npy file
        mds_path = "data/mds.npy"
        if os.path.exists(mds_path):
            mds_projection = np.load(mds_path)
            
            # Also load the true labels for visualization
            with open("data/point_cloud_data.json", "r") as f:
                point_data = json.load(f)
                labels = point_data["true_labels"]
            
            return {
                "projection": mds_projection.tolist(),
                "labels": labels
            }
        return {"error": "MDS projection not found"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/lda")
async def get_lda():
    try:
        # Load LDA projection from .npy file
        lda_path = "data/lda.npy"
        if os.path.exists(lda_path):
            lda_projection = np.load(lda_path)
            
            # Also load the true labels for visualization
            with open("data/point_cloud_data.json", "r") as f:
                point_data = json.load(f)
                labels = point_data["true_labels"]
            
            return {
                "projection": lda_projection.tolist(),
                "labels": labels
            }
        return {"error": "LDA projection not found"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload_model")
async def upload_model(file: UploadFile = File(...)):
    try:
        # Create models directory if it doesn't exist
        models_dir = Path("data/models")
        models_dir.mkdir(exist_ok=True)
        
        # Save the uploaded file
        file_path = models_dir / file.filename
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Validate that it's a valid pickle/joblib file
        try:
            if file.filename.endswith('.joblib'):
                model = joblib.load(file_path)
            else:
                with open(file_path, 'rb') as f:
                    model = pickle.load(f)
        except Exception as e:
            # Remove invalid file
            os.remove(file_path)
            return {"success": False, "error": f"Invalid model file: {str(e)}"}
        
        # Get model name without extension
        model_name = Path(file.filename).stem
        
        # Update config.json to include the new model
        with open("src/config.json", "r") as f:
            config_data = json.load(f)
        
        if "Model" not in config_data:
            config_data["Model"] = []
        
        if model_name not in config_data["Model"]:
            config_data["Model"].append(model_name)
            
            with open("src/config.json", "w") as f:
                json.dump(config_data, f, indent=2)
        
        return {
            "success": True,
            "model_name": model_name,
            "message": f"Model {model_name} uploaded successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}