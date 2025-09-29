import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Alert, CircularProgress, Box } from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'

interface User {
  id: number
  full_name?: string
  tg_id: number
  age?: number
  phone?: string
}

const columns: GridColDef<User>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'full_name', headerName: 'Имя', flex: 1 },
  { field: 'tg_id', headerName: 'Telegram ID', width: 150 },
  { field: 'age', headerName: 'Возраст', width: 120 },
  { field: 'phone', headerName: 'Телефон', width: 150 }
]

const UsersPage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await apiClient.get<User[]>('/users')
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
    return <Alert severity="error">Не удалось загрузить пользователей</Alert>
  }

  return (
    <Box height={400}>
      <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
    </Box>
  )
}

export default UsersPage
