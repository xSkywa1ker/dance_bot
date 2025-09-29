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
  user_full_name?: string | null
  slot_starts_at?: string | null
  slot_direction_name?: string | null
}

const columns: GridColDef<Booking>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'status', headerName: 'Статус', width: 120 },
  {
    field: 'slot_starts_at',
    headerName: 'Время занятия',
    flex: 1,
    valueFormatter: (params) =>
      params.value ? dayjs(params.value as string).format('DD.MM.YYYY HH:mm') : '—'
  },
  {
    field: 'slot_direction_name',
    headerName: 'Направление',
    flex: 1,
    valueGetter: (params) => params.row.slot_direction_name ?? '—'
  },
  {
    field: 'user_full_name',
    headerName: 'ФИО',
    flex: 1,
    valueGetter: (params) => params.row.user_full_name ?? '—'
  },
  {
    field: 'created_at',
    headerName: 'Создано',
    width: 180,
    valueFormatter: (params) => dayjs(params.value as string).format('DD.MM.YYYY HH:mm')
  },
  { field: 'user_id', headerName: 'ID пользователя', width: 140 },
  { field: 'class_slot_id', headerName: 'ID слота', width: 120 }
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
