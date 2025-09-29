import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Alert, CircularProgress, Box } from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import dayjs from 'dayjs'

interface Payment {
  id: number
  status: string
  amount: number
  currency: string
  purpose: string
  user_id: number
  product_id: number | null
  class_slot_id: number | null
  created_at: string
}

const columns: GridColDef<Payment>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  {
    field: 'created_at',
    headerName: 'Создано',
    flex: 1,
    valueFormatter: (params) => dayjs(params.value as string).format('DD.MM.YYYY HH:mm')
  },
  {
    field: 'amount',
    headerName: 'Сумма',
    width: 120,
    valueFormatter: (params) => `${params.value} ${(params.row.currency as string) ?? '₽'}`
  },
  { field: 'currency', headerName: 'Валюта', width: 100 },
  { field: 'status', headerName: 'Статус', width: 140 },
  { field: 'purpose', headerName: 'Назначение', width: 160 },
  { field: 'user_id', headerName: 'Пользователь', width: 140 },
  { field: 'product_id', headerName: 'Продукт', width: 120 },
  { field: 'class_slot_id', headerName: 'Слот', width: 120 }
]

const PaymentsPage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['payments'],
    queryFn: async () => {
      const response = await apiClient.get<Payment[]>('/payments')
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
    return <Alert severity="error">Не удалось загрузить платежи</Alert>
  }

  return (
    <Box height={400}>
      <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
    </Box>
  )
}

export default PaymentsPage
