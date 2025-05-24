import socket
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestTCPServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
    
    def start(self):
        """Start the TCP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"TCP Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"New connection from {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.start()
                    
                except Exception as e:
                    logger.error(f"Error accepting connection: {str(e)}")
                    break
                    
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, address):
        """Handle client connection and receive logs."""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Decode and print the received log
                log_data = data.decode('utf-8').strip()
                logger.info(f"Received log from {address}:")
                logger.info("-" * 50)
                logger.info(log_data)
                logger.info("-" * 50)
                
        except Exception as e:
            logger.error(f"Error handling client {address}: {str(e)}")
        finally:
            client_socket.close()
            logger.info(f"Connection closed for {address}")
    
    def stop(self):
        """Stop the TCP server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("TCP Server stopped")

if __name__ == "__main__":
    server = TestTCPServer()
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        server.stop() 