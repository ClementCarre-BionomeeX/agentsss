#!/bin/bash

# Configuration Variables
ENV_NAME="agents"
PYTHON_VERSION="3.13"
LIBRARIES=() 
PIPLIBRARIES=("streamlit" "requests")

# Function to check if an environment exists
env_exists() {
    local manager="$1"
    local env_name="$2"

    if [[ "$manager" == "micromamba" ]]; then
        micromamba env list | awk '{print $1}' | grep -q "^${env_name}$"
    elif [[ "$manager" == "conda" ]]; then
        conda env list | awk '{print $1}' | grep -q "^${env_name}$"
    else
        return 1
    fi
}

# Function to create environment
create_env() {
    local manager="$1"
    local env_name="$2"
    local python_version="$3"

    echo "Creating environment '$env_name' using $manager with Python $python_version..."
    
    if [[ "$manager" == "micromamba" ]]; then
        micromamba create -n "$env_name" python="$python_version" -y
    elif [[ "$manager" == "conda" ]]; then
        conda create -n "$env_name" python="$python_version" -y
    else
        echo "Error: Unknown package manager."
        exit 1
    fi
}

# Function to install Conda/Micromamba packages
install_packages() {
    local manager="$1"
    local env_name="$2"
    shift 2
    local packages=("$@")

    if [[ ${#packages[@]} -eq 0 ]]; then
        echo "No conda/micromamba packages to install."
        return
    fi

    echo "Installing required packages: ${packages[*]}..."

    if [[ "$manager" == "micromamba" ]]; then
        micromamba install -n "$env_name" "${packages[@]}" -y
    elif [[ "$manager" == "conda" ]]; then
        conda install -n "$env_name" "${packages[@]}" -y
    else
        echo "Error: Unknown package manager."
        exit 1
    fi
}

# Function to install Pip packages inside the environment
install_pip_packages() {
    local manager="$1"
    local env_name="$2"
    shift 2
    local pip_packages=("$@")

    if [[ ${#pip_packages[@]} -eq 0 ]]; then
        echo "No pip packages to install."
        return
    fi

    echo "Installing pip packages: ${pip_packages[*]}..."
    
    if [[ "$manager" == "micromamba" ]]; then
        micromamba run -n "$env_name" pip install "${pip_packages[@]}"
    elif [[ "$manager" == "conda" ]]; then
        # Conda requires activating the environment before using pip
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate "$env_name"
        pip install "${pip_packages[@]}"
    fi
}

# Function to remove the environment
remove_env() {
    local manager="$1"
    local env_name="$2"

    echo "Removing existing environment '$env_name'..."
    
    if [[ "$manager" == "micromamba" ]]; then
        micromamba env remove -n "$env_name" -y
    elif [[ "$manager" == "conda" ]]; then
        conda remove -n "$env_name" --all -y
    fi
}

# Function to remove and rebuild the environment
rebuild_env() {

    local manager="$1"
    local env_name="$2"
    
    remove_env "$manager" "$env_name"
  
    create_env "$manager" "$env_name" "$PYTHON_VERSION"
    install_packages "$manager" "$env_name" "${LIBRARIES[@]}"
    install_pip_packages "$manager" "$env_name" "${PIPLIBRARIES[@]}"
}

# Function to activate environment
activate_env() {
    local manager="$1"
    local env_name="$2"

    echo "Activating environment '$env_name' using $manager..."
    
    if [[ "$manager" == "micromamba" ]]; then
        micromamba activate "$env_name"
    elif [[ "$manager" == "conda" ]]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate "$env_name"
    else
        echo "Error: Activation failed."
        exit 1
    fi
}

# Determine the environment manager
if command -v micromamba &> /dev/null; then
    MANAGER="micromamba"
elif command -v conda &> /dev/null; then
    MANAGER="conda"
else
    echo "Error: Neither micromamba nor conda found. Please install one of them."
    exit 1
fi

# Check for --rebuild flag
if [[ "$1" == "--rebuild" ]]; then
    rebuild_env "$MANAGER" "$ENV_NAME"
else
    # Check if the environment exists, create it if necessary
    if env_exists "$MANAGER" "$ENV_NAME"; then
        echo "Environment '$ENV_NAME' already exists."
    else
        create_env "$MANAGER" "$ENV_NAME" "$PYTHON_VERSION"
        install_packages "$MANAGER" "$ENV_NAME" "${LIBRARIES[@]}"
        install_pip_packages "$MANAGER" "$ENV_NAME" "${PIPLIBRARIES[@]}"
    fi
fi

if [[ "$1" == "--remove" ]]; then
    remove_env "$MANAGER" "$ENV_NAME"
fi

# Activate the environment
activate_env "$MANAGER" "$ENV_NAME"
