import subprocess

def print_file(filename):
    try:
        subprocess.run(["lp", filename], check=True)
        print(f"Sent {filename} to the default printer.")
    except subprocess.CalledProcessError as e:
        print(f"Error printing {filename}. Error code: {e.returncode}")
    except FileNotFoundError:
        print("lp command not found. Ensure CUPS is installed and in your PATH.")

# Example usage:
print_file("requirements.txt")
