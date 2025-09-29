import {
  CssBaseline,
  ThemeProvider,
  createTheme,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Tabs,
  Tab,
  CircularProgress,
  Button
} from '@mui/material'
import { useState } from 'react'
import DashboardPage from './pages/Dashboard'
import DirectionsPage from './pages/Directions'
import SchedulePage from './pages/Schedule'
import ProductsPage from './pages/Products'
import BookingsPage from './pages/Bookings'
import UsersPage from './pages/Users'
import SettingsPage from './pages/Settings'
import LoginPage from './pages/Login'
import { useAuth } from './auth/AuthContext'

const theme = createTheme()

const tabs = [
  { label: 'Дашборд', component: <DashboardPage /> },
  { label: 'Направления', component: <DirectionsPage /> },
  { label: 'Расписание', component: <SchedulePage /> },
  { label: 'Продукты', component: <ProductsPage /> },
  { label: 'Бронирования', component: <BookingsPage /> },
  { label: 'Пользователи', component: <UsersPage /> },
  { label: 'Настройки', component: <SettingsPage /> }
]

function App() {
  const [currentTab, setCurrentTab] = useState(0)
  const { user, initializing, logout, clearError } = useAuth()

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {initializing ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
          <CircularProgress size={56} />
        </Box>
      ) : !user ? (
        <LoginPage />
      ) : (
        <>
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Dance Studio Admin
              </Typography>
              <Typography variant="body2" sx={{ mr: 3 }}>
                {user.email}
              </Typography>
              <Button
                color="inherit"
                onClick={() => {
                  clearError()
                  logout()
                }}
                sx={{ textTransform: 'none', fontWeight: 500 }}
              >
                Выйти
              </Button>
            </Toolbar>
          </AppBar>
          <Container maxWidth="lg">
            <Box mt={4}>
              <Tabs
                value={currentTab}
                onChange={(_, value) => setCurrentTab(value)}
                variant="scrollable"
                scrollButtons
                allowScrollButtonsMobile
              >
                {tabs.map((tab, index) => (
                  <Tab key={index} label={tab.label} />
                ))}
              </Tabs>
              <Box mt={4}>{tabs[currentTab].component}</Box>
            </Box>
          </Container>
        </>
      )}
    </ThemeProvider>
  )
}

export default App
