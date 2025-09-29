import { useState, type ChangeEvent, type FormEvent } from 'react'
import {
  Alert,
  Avatar,
  Box,
  Button,
  CircularProgress,
  Container,
  Paper,
  TextField,
  Typography
} from '@mui/material'
import { useAuth } from '../auth/AuthContext'

const LoginPage = () => {
  const { login, error, clearError } = useAuth()
  const [loginValue, setLoginValue] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    try {
      await login(loginValue, password)
    } catch (submitError) {
      // error is handled by the auth context
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLoginChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (error) {
      clearError()
    }
    setLoginValue(event.target.value)
  }

  const handlePasswordChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (error) {
      clearError()
    }
    setPassword(event.target.value)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #e0f2ff 0%, #f5f7ff 100%)',
        py: 6,
        px: 2
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={8}
          sx={{
            p: { xs: 4, md: 6 },
            borderRadius: 4,
            backdropFilter: 'blur(12px)',
            backgroundColor: 'rgba(255,255,255,0.95)'
          }}
        >
          <Box textAlign="center" mb={3}>
            <Avatar
              sx={{
                bgcolor: 'primary.main',
                width: 72,
                height: 72,
                mx: 'auto',
                mb: 2,
                fontSize: 28,
                fontWeight: 600
              }}
            >
              DS
            </Avatar>
            <Typography component="h1" variant="h4" fontWeight={600} gutterBottom>
              Добро пожаловать
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Войдите в панель управления студии, чтобы продолжить
            </Typography>
          </Box>

          <Box component="form" onSubmit={handleSubmit} display="flex" flexDirection="column" gap={2}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Логин"
              type="text"
              value={loginValue}
              onChange={handleLoginChange}
              placeholder="admin"
              fullWidth
              autoComplete="username"
              required
            />
            <TextField
              label="Пароль"
              type="password"
              value={password}
              onChange={handlePasswordChange}
              fullWidth
              autoComplete="current-password"
              required
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={!loginValue || !password || isSubmitting}
              sx={{
                mt: 1,
                py: 1.5,
                borderRadius: 3,
                fontSize: 16,
                fontWeight: 600,
                textTransform: 'none'
              }}
            >
              {isSubmitting ? <CircularProgress size={26} color="inherit" /> : 'Войти'}
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}

export default LoginPage

