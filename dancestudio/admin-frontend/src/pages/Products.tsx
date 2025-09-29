import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Alert, CircularProgress, Box } from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'

interface Product {
  id: number
  name: string
  price: number
  type: string
  is_active: boolean
}

const columns: GridColDef<Product>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'name', headerName: 'Название', flex: 1 },
  { field: 'type', headerName: 'Тип', width: 150 },
  { field: 'price', headerName: 'Цена', width: 150 },
  { field: 'is_active', headerName: 'Активен', type: 'boolean', width: 120 }
]

const ProductsPage = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: async () => {
      const response = await apiClient.get<Product[]>('/products')
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
    return <Alert severity="error">Не удалось загрузить продукты</Alert>
  }

  return (
    <Box height={400}>
      <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
    </Box>
  )
}

export default ProductsPage
