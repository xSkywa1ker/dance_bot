import { Card, CardContent, Grid, Typography } from '@mui/material'

const stats = [
  { title: 'Записей сегодня', value: 12 },
  { title: 'Посещаемость', value: '85%' },
  { title: 'Выручка (неделя)', value: '120 000 ₽' }
]

const DashboardPage = () => (
  <Grid container spacing={2}>
    {stats.map((item) => (
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

export default DashboardPage
