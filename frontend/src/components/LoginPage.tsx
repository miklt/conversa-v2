import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.endsWith('@usp.br')) {
      setMessage('Email deve terminar com @usp.br');
      setIsSuccess(false);
      return;
    }

    setIsSubmitting(true);
    setMessage('');

    try {
      const response = await login(email);
      setMessage(`${response.message}. Verifique sua caixa de entrada!`);
      setIsSuccess(true);
      setEmail(''); // Clear the form
    } catch (error: any) {
      console.error('Login error:', error);
      setMessage(
        error.response?.data?.detail || 
        'Erro ao enviar magic link. Tente novamente.'
      );
      setIsSuccess(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="login-logos">
            <img src="/logo_poli.png" alt="Escola Politécnica USP" className="login-logo-poli" />
            <img src="/logo_pcs.png" alt="PCS - Engenharia de Computação" className="login-logo-pcs" />
          </div>
          <h1>Bate papo com os Relatórios de Estágio</h1>
          <p>Sistema de Consulta de Relatórios de Estágio - POLI - PCS</p>
        </div>

        <div className="login-form-container">
          <h2>Acessar o Sistema</h2>
          <p className="login-description">
            Digite seu email @usp.br para receber um link de acesso
          </p>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="email">Email USP</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu.nome@usp.br"
                required
                disabled={isSubmitting}
                className="email-input"
              />
            </div>

            <button 
              type="submit" 
              disabled={isSubmitting || !email}
              className={`login-button ${isSubmitting ? 'loading' : ''}`}
            >
              {isSubmitting ? 'Enviando...' : 'Enviar Link de Acesso'}
            </button>
          </form>

          {message && (
            <div className={`message ${isSuccess ? 'success' : 'error'}`}>
              {message}
            </div>
          )}

          {isSuccess && (
            <div className="success-instructions">
              <h3>📧 Link enviado!</h3>
              <p>
                Verifique seu email e clique no link para acessar o sistema.
                O link expira em 15 minutos.
              </p>
              <p className="spam-notice">
                💡 <strong>Dica:</strong> Se não encontrar o email, verifique a pasta de spam.
              </p>
            </div>
          )}
        </div>

        <div className="login-footer">
          <p>
            Sistema desenvolvido para análise de dados de estágios de 
            Engenharia Elétrica da Universidade de São Paulo
          </p>
        </div>
      </div>
    </div>
  );
}