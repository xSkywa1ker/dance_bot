import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Alert, CircularProgress, List, ListItem, ListItemText, Box } from '@mui/material'
import dayjs from 'dayjs'

interface Slot {
  id: number
  starts_at: string
  duration_min: number
  capacity: number
}

const SchedulePage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['slots'],
    queryFn: async () => {
      const response = await apiClient.get<Slot[]>('/slots')
      return response.data
    }
  })

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">Не удалось загрузить расписание</Alert>
  }

  return (
    <List>
      {data?.map((slot) => (
        <ListItem key={slot.id} divider>
          <ListItemText
            primary={dayjs(slot.starts_at).format('DD.MM.YYYY HH:mm')}
            secondary={`Длительность: ${slot.duration_min} мин · Мест: ${slot.capacity}`}
          />
        </ListItem>
      ))}
    </List>
  )
}

export default SchedulePage
