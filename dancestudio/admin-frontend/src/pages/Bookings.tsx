import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Alert, CircularProgress, Box } from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import dayjs from 'dayjs'

interface Booking {
  id: number
  status: string
  created_at: string
  user_id: number
  class_slot_id: number
}

const columns: GridColDef<Booking>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'status', headerName: 'Статус', width: 120 },
  {
    field: 'created_at',
    headerName: 'Создано',
    flex: 1,
    valueFormatter: (params) => dayjs(params.value as string).format('DD.MM.YYYY HH:mm')
  },
  { field: 'user_id', headerName: 'Пользователь', width: 150 },
  { field: 'class_slot_id', headerName: 'Слот', width: 150 }
]

const BookingsPage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['bookings'],
    queryFn: async () => {
      const response = await apiClient.get<Booking[]>('/bookings')
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
    return <Alert severity="error">Не удалось загрузить бронирования</Alert>
  }

  return (
    <Box height={400}>
      <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
    </Box>
  )
}

export default BookingsPage
