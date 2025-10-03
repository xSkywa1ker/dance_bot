import { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Card, CardContent, CircularProgress, Grid, Typography } from '@mui/material'

import { apiClient } from '../api/client'

type DashboardStats = {
  total: number
  confirmed: number
  bookings_today: number
  attendance_rate: number
  weekly_revenue: number
}

const DashboardPage = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const fetchStats = async () => {
      try {
        const response = await apiClient.get<DashboardStats>('/bookings/stats')
        if (isMounted) {
          setStats(response.data)
        }
      } catch (err) {
        if (isMounted) {
          setError('Не удалось загрузить статистику')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    void fetchStats()

    return () => {
      isMounted = false
    }
  }, [])

  const statItems = useMemo(() => {
    if (!stats) {
      return [
        { title: 'Записей сегодня', value: '0' },
        { title: 'Посещаемость', value: '0%' },
        { title: 'Выручка (неделя)', value: '0 ₽' }
      ]
    }

    const attendance = `${Math.round(stats.attendance_rate)}%`
    const revenueFormatter = new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    })
    const revenue = revenueFormatter.format(stats.weekly_revenue)

    return [
      { title: 'Записей сегодня', value: stats.bookings_today.toString() },
      { title: 'Посещаемость', value: attendance },
      { title: 'Выручка (неделя)', value: revenue }
    ]
  }, [stats])

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  return (
    <Grid container spacing={2}>
      {statItems.map((item) => (
        <Grid item xs={12} md={4} key={item.title}>
          <Card>
            <CardContent>
              <Typography variant="h6">{item.title}</Typography>
              <Typography variant="h4">{item.value}</Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

export default DashboardPage
