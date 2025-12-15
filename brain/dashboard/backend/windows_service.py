"""
VIRTUS Dashboard Backend - Windows Service
==========================================

Serviço Windows para rodar o backend com auto-restart.
Usa win32service para integração com o Windows.
"""

import os
import sys
import time
import socket
import logging
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

# Configuração de logging
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "dashboard_service.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VirtusDashboardService:
    """
    Gerenciador do serviço de backend VIRTUS.
    
    Funcionalidades:
    - Inicia o servidor Uvicorn
    - Monitora a saúde do serviço
    - Reinicia automaticamente em caso de falha
    - Logging completo
    """
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.process = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_cooldown = 30  # segundos entre restarts
        self.last_restart = None
        
        # Configurações do servidor
        self.host = os.getenv("VIRTUS_HOST", "0.0.0.0")
        self.port = int(os.getenv("VIRTUS_PORT", "8000"))
        
    def check_port_available(self) -> bool:
        """Verifica se a porta está disponível."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, self.port))
                return True
        except socket.error:
            return False
    
    def kill_existing_process(self):
        """Mata processos existentes na porta."""
        try:
            # Windows: encontrar e matar processo na porta
            result = subprocess.run(
                f'netstat -ano | findstr :{self.port}',
                shell=True, capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if f':{self.port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                        logger.info(f"Processo {pid} encerrado na porta {self.port}")
                        time.sleep(2)
        except Exception as e:
            logger.warning(f"Erro ao tentar encerrar processo: {e}")
    
    def start_server(self) -> bool:
        """Inicia o servidor Uvicorn."""
        try:
            # Verifica se porta está em uso
            if not self.check_port_available():
                logger.warning(f"Porta {self.port} em uso, tentando liberar...")
                self.kill_existing_process()
                time.sleep(2)
            
            # Define o diretório de trabalho
            os.chdir(str(self.backend_dir))
            
            # Comando para iniciar o servidor
            cmd = [
                sys.executable,
                "-m", "uvicorn",
                "main:app",
                "--host", self.host,
                "--port", str(self.port),
                "--workers", "2",
                "--log-level", "info"
            ]
            
            logger.info(f"Iniciando servidor: {' '.join(cmd)}")
            
            # Inicia o processo
            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Aguarda um pouco e verifica se iniciou
            time.sleep(3)
            
            if self.process.poll() is None:
                logger.info(f"✓ Servidor iniciado com sucesso na porta {self.port}")
                return True
            else:
                logger.error("✗ Servidor falhou ao iniciar")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def check_health(self) -> bool:
        """Verifica se o servidor está respondendo."""
        try:
            import urllib.request
            url = f"http://localhost:{self.port}/health"
            response = urllib.request.urlopen(url, timeout=5)
            return response.status == 200
        except:
            # Tenta verificar se o processo ainda está rodando
            if self.process and self.process.poll() is None:
                return True
            return False
    
    def restart_server(self):
        """Reinicia o servidor."""
        now = datetime.now()
        
        # Verifica cooldown
        if self.last_restart:
            elapsed = (now - self.last_restart).total_seconds()
            if elapsed < self.restart_cooldown:
                logger.warning(f"Aguardando cooldown... ({self.restart_cooldown - elapsed:.0f}s)")
                time.sleep(self.restart_cooldown - elapsed)
        
        # Verifica limite de restarts
        if self.restart_count >= self.max_restarts:
            logger.error(f"Limite de restarts atingido ({self.max_restarts}). Parando serviço.")
            self.running = False
            return
        
        logger.info(f"Reiniciando servidor (tentativa {self.restart_count + 1}/{self.max_restarts})...")
        
        # Para o servidor atual
        self.stop_server()
        time.sleep(2)
        
        # Inicia novamente
        if self.start_server():
            self.restart_count += 1
            self.last_restart = now
        else:
            logger.error("Falha ao reiniciar servidor")
    
    def stop_server(self):
        """Para o servidor."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.warning(f"Erro ao parar servidor: {e}")
            finally:
                self.process = None
        
        logger.info("Servidor parado")
    
    def run(self):
        """Loop principal do serviço."""
        logger.info("="*60)
        logger.info("VIRTUS Dashboard Service Iniciando")
        logger.info(f"Backend: {self.backend_dir}")
        logger.info(f"Porta: {self.port}")
        logger.info("="*60)
        
        self.running = True
        
        # Inicia o servidor
        if not self.start_server():
            logger.error("Falha ao iniciar servidor. Tentando novamente...")
            time.sleep(5)
            if not self.start_server():
                logger.error("Falha definitiva ao iniciar. Saindo.")
                return
        
        # Loop de monitoramento
        check_interval = 30  # segundos
        
        while self.running:
            try:
                time.sleep(check_interval)
                
                # Verifica saúde do servidor
                if not self.check_health():
                    logger.warning("Servidor não está respondendo!")
                    self.restart_server()
                else:
                    # Reset contador de restarts após funcionamento estável
                    if self.restart_count > 0:
                        elapsed_since_restart = (datetime.now() - self.last_restart).total_seconds()
                        if elapsed_since_restart > 300:  # 5 minutos estável
                            logger.info("Servidor estável. Resetando contador de restarts.")
                            self.restart_count = 0
                
            except KeyboardInterrupt:
                logger.info("Interrupção recebida. Parando serviço...")
                break
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
        
        # Cleanup
        self.stop_server()
        logger.info("VIRTUS Dashboard Service Encerrado")


def main():
    """Ponto de entrada principal."""
    service = VirtusDashboardService()
    service.run()


if __name__ == "__main__":
    main()
