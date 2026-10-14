import yaml
import json
import re

def get_default_boutique_topology():
    return {
        "frontend": {
            "dependencies": ["cartservice", "productcatalogservice", "checkoutservice", "recommendationservice", "adservice", "currencyservice", "shippingservice"],
            "env": {},
            "dependents": []
        },
        "checkoutservice": {
            "dependencies": ["cartservice", "productcatalogservice", "currencyservice", "paymentservice", "shippingservice", "emailservice"],
            "env": {},
            "dependents": ["frontend"]
        },
        "cartservice": {
            "dependencies": ["redis-cart"],
            "env": {},
            "dependents": ["frontend", "checkoutservice"]
        },
        "productcatalogservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["frontend", "checkoutservice", "recommendationservice"]
        },
        "recommendationservice": {
            "dependencies": ["productcatalogservice"],
            "env": {},
            "dependents": ["frontend"]
        },
        "paymentservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["checkoutservice"]
        },
        "emailservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["checkoutservice"]
        },
        "shippingservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["frontend", "checkoutservice"]
        },
        "currencyservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["frontend", "checkoutservice"]
        },
        "adservice": {
            "dependencies": [],
            "env": {},
            "dependents": ["frontend"]
        },
        "redis-cart": {
            "dependencies": [],
            "env": {},
            "dependents": ["cartservice"]
        }
    }

def discover_topology(manifest_path=None):
    if not manifest_path:
        return get_default_boutique_topology()
        
    try:
        with open(manifest_path, 'r') as f:
            docs = yaml.safe_load_all(f)
            services = {}
            
            for doc in docs:
                if not doc:
                    continue
                
                kind = doc.get("kind")
                if kind == "Deployment":
                    name = doc["metadata"]["name"]
                    if name not in services:
                        services[name] = {"dependencies": [], "env": {}}
                    
                    containers = doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    for container in containers:
                        for env in container.get("env", []):
                            env_name = env.get("name", "")
                            env_value = env.get("value", "")
                            services[name]["env"][env_name] = env_value
                            
                            # Detect dependencies: typical format is "SERVICENAME_ADDR" or pointing to "servicename:port"
                            if "_ADDR" in env_name:
                                dep_name = env_value.split(":")[0]
                                # Clean up if it's a URL
                                if "://" in dep_name:
                                    dep_name = dep_name.split("://")[1]
                                if dep_name not in services[name]["dependencies"] and dep_name != name:
                                    services[name]["dependencies"].append(dep_name)
        
        # Compute downstream dependents
        for srv in services.values():
            srv["dependents"] = []
        
        for name, srv_data in services.items():
            for dep in srv_data["dependencies"]:
                if dep in services:
                    services[dep]["dependents"].append(name)
                    
        return services if services else get_default_boutique_topology()
    except (FileNotFoundError, IOError):
        return get_default_boutique_topology()

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "../microservices-demo/release/kubernetes-manifests.yaml"
    graph = discover_topology(path)
    print(json.dumps(graph, indent=2))
