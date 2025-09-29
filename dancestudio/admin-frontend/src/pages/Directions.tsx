import { useQuery } from '@tanstack/react-query'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { Box, CircularProgress, Alert } from '@mui/material'
import { apiClient } from '../api/client'

type Direction = {
  id: number
  name: string
  description?: string
  is_active: boolean
}

const columns: GridColDef<Direction>[] = [
  { field: 'id', headerName: 'ID', width: 90 },
  { field: 'name', headerName: 'Название', flex: 1 },
  { field: 'description', headerName: 'Описание', flex: 2 },
  { field: 'is_active', headerName: 'Активно', type: 'boolean', width: 120 }
]

const DirectionsPage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['directions'],
    queryFn: async () => {
      const response = await apiClient.get<Direction[]>('/directions')
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
    return <Alert severity="error">Не удалось загрузить направления</Alert>
  }

  return (
    <Box height={400}>
      <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
    </Box>
  )
}

export default DirectionsPage
