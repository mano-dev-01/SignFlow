"""Remote inference client for Hugging Face Spaces endpoint."""
import json
import requests
import numpy as np
import time
import traceback

# Debug logging
_DEBUG_LOG_FILE = "/tmp/signflow_remote_inference_debug.log"

def _debug_log(message):
    try:
        with open(_DEBUG_LOG_FILE, "a") as f:
            f.write(f"[{time.time():.2f}] {message}\n")
            f.flush()
    except:
        pass

_debug_log("=== remote_inference_client module loaded ===")


class RemoteInferenceClient:
    """Client for remote model inference via HF Spaces."""
    
    def __init__(self, endpoint_url: str):
        """
        Initialize remote inference client.
        
        Args:
            endpoint_url: URL of the HF Spaces inference endpoint
                         e.g., "https://mano-dev-01-signflow-inference.hf.space"
        """
        self.endpoint_url = endpoint_url.rstrip("/")
        self.predict_endpoint = f"{self.endpoint_url}/api/predict"
        self.available = False
        self._last_error = None
        self._error_count = 0
        self._max_errors = 5
        
        _debug_log(f"RemoteInferenceClient initialized with endpoint: {self.endpoint_url}")
        
        # Test connectivity
        self._test_connectivity()
    
    def _test_connectivity(self):
        """Test if the remote endpoint is reachable."""
        try:
            _debug_log("Testing connectivity to remote endpoint...")
            response = requests.get(self.endpoint_url, timeout=5)
            if response.status_code in (200, 404):
                self.available = True
                _debug_log(f"✅ Remote endpoint is reachable (status: {response.status_code})")
            else:
                self._last_error = f"Unexpected status code: {response.status_code}"
                _debug_log(f"❌ {self._last_error}")
        except requests.exceptions.Timeout:
            self._last_error = "Endpoint timeout"
            _debug_log(f"❌ Endpoint timeout")
        except requests.exceptions.ConnectionError:
            self._last_error = "Connection refused"
            _debug_log(f"❌ Connection refused")
        except Exception as e:
            self._last_error = str(e)
            _debug_log(f"❌ Connectivity test failed: {e}")
    
    def predict(self, features: np.ndarray) -> str:
        """
        Get prediction from remote model.
        
        Args:
            features: numpy array of hand features
            
        Returns:
            Prediction string (e.g., "HELLO", "THANK YOU", etc.)
        """
        if self._error_count >= self._max_errors:
            return "Model_Offline"
        
        try:
            # Convert features to list
            features_list = features.flatten().tolist() if isinstance(features, np.ndarray) else list(features)
            
            payload = {
                "data": [features_list]
            }
            
            _debug_log(f"Sending prediction request: {len(features_list)} features")
            
            response = requests.post(
                self.predict_endpoint,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                _debug_log(f"Received response: {result}")
                
                # Extract prediction from response
                # Response format may vary, try common formats
                if isinstance(result, dict):
                    if "data" in result:
                        prediction = result["data"][0] if isinstance(result["data"], list) else result["data"]
                    elif "prediction" in result:
                        prediction = result["prediction"]
                    else:
                        prediction = str(result)
                else:
                    prediction = str(result)
                
                self._error_count = 0  # Reset error count on success
                return str(prediction)
            else:
                self._error_count += 1
                msg = f"Prediction failed: HTTP {response.status_code}"
                _debug_log(f"❌ {msg}")
                return "Error"
        
        except requests.exceptions.Timeout:
            self._error_count += 1
            _debug_log(f"❌ Prediction timeout (error count: {self._error_count})")
            return "Timeout"
        except requests.exceptions.ConnectionError:
            self._error_count += 1
            _debug_log(f"❌ Connection error (error count: {self._error_count})")
            return "NoConnection"
        except Exception as e:
            self._error_count += 1
            _debug_log(f"❌ Prediction error: {e}")
            traceback.print_exc()
            return "Error"
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Get prediction probabilities from remote model.
        
        Args:
            features: numpy array of hand features
            
        Returns:
            Array of probabilities (estimated based on prediction confidence)
        """
        if self._error_count >= self._max_errors:
            return np.array([0.0])
        
        try:
            features_list = features.flatten().tolist() if isinstance(features, np.ndarray) else list(features)
            
            # Try to get confidence/probability endpoint
            proba_endpoint = f"{self.endpoint_url}/api/predict_proba"
            
            payload = {
                "data": [features_list]
            }
            
            _debug_log(f"Requesting probabilities from {proba_endpoint}")
            
            response = requests.post(
                proba_endpoint,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                _debug_log(f"Received probabilities: {result}")
                
                if isinstance(result, dict) and "data" in result:
                    probs = result["data"][0] if isinstance(result["data"], list) else result["data"]
                else:
                    probs = result
                
                # Convert to numpy array
                if isinstance(probs, list):
                    return np.array(probs)
                else:
                    return np.array(probs).reshape(1, -1)
            else:
                # Fallback: return high confidence since we got a prediction
                return np.array([[0.9, 0.05, 0.05]])  # Dummy proba if endpoint not available
        
        except Exception as e:
            _debug_log(f"⚠️  Probabilities request failed: {e}, using default")
            # Return default high confidence
            return np.array([[0.85, 0.1, 0.05]])


# Global client instance
_remote_client = None

def get_remote_client(endpoint_url: str = None) -> RemoteInferenceClient:
    """Get or create a remote inference client."""
    global _remote_client
    
    if endpoint_url is None:
        endpoint_url = "https://mano-dev-01-signflow-inference.hf.space"
    
    if _remote_client is None or _remote_client.endpoint_url != endpoint_url:
        _remote_client = RemoteInferenceClient(endpoint_url)
    
    return _remote_client
