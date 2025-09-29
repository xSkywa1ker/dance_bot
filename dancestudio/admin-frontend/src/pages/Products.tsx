import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import {
  Alert,
  CircularProgress,
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Stack,
  FormControlLabel,
  Switch
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import { useForm, Controller } from 'react-hook-form'

interface Product {
  id: number
  name: string
  description?: string | null
  price: number
  type: string
  is_active: boolean
  classes_count?: number | null
  validity_days?: number | null
  direction_limit_id?: number | null
}

type ProductFormValues = {
  name: string
  type: string
  description: string
  price: number
  classes_count?: number | null
  validity_days?: number | null
  direction_limit_id?: number | null
  is_active: boolean
}

const defaultValues: ProductFormValues = {
  name: '',
  type: '',
  description: '',
  price: 0,
  classes_count: undefined,
  validity_days: undefined,
  direction_limit_id: undefined,
  is_active: true
}

const normalizeOptionalNumber = (value: number | null | undefined) =>
  typeof value === 'number' && !Number.isNaN(value) ? value : null

const ProductsPage = () => {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: async () => {
      const response = await apiClient.get<Product[]>('/products')
      return response.data
    }
  })

  const { register, handleSubmit, reset, control, formState } = useForm<ProductFormValues>({
    defaultValues
  })

  const openCreateDialog = () => {
    setEditingProduct(null)
    reset(defaultValues)
    setDialogOpen(true)
  }

  const openEditDialog = (product: Product) => {
    setEditingProduct(product)
    reset({
      name: product.name,
      type: product.type,
      description: product.description ?? '',
      price: product.price,
      classes_count: product.classes_count ?? undefined,
      validity_days: product.validity_days ?? undefined,
      direction_limit_id: product.direction_limit_id ?? undefined,
      is_active: product.is_active
    })
    setDialogOpen(true)
  }

  const closeDialog = () => setDialogOpen(false)

  const createMutation = useMutation({
    mutationFn: async (payload: ProductFormValues) => {
      const body = {
        ...payload,
        description: payload.description.trim() || null,
        classes_count: normalizeOptionalNumber(payload.classes_count),
        validity_days: normalizeOptionalNumber(payload.validity_days),
        direction_limit_id: normalizeOptionalNumber(payload.direction_limit_id)
      }
      const response = await apiClient.post<Product>('/products', body)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      closeDialog()
    }
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ProductFormValues }) => {
      const body = {
        ...payload,
        description: payload.description.trim() || null,
        classes_count: normalizeOptionalNumber(payload.classes_count),
        validity_days: normalizeOptionalNumber(payload.validity_days),
        direction_limit_id: normalizeOptionalNumber(payload.direction_limit_id)
      }
      const response = await apiClient.patch<Product>(`/products/${id}`, body)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      closeDialog()
    }
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/products/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    }
  })

  const onSubmit = (values: ProductFormValues) => {
    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, payload: values })
    } else {
      createMutation.mutate(values)
    }
  }

  const handleDelete = (product: Product) => {
    if (window.confirm(`Удалить продукт «${product.name}»?`)) {
      deleteMutation.mutate(product.id)
    }
  }

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 80 },
    { field: 'name', headerName: 'Название', flex: 1, minWidth: 180 },
    { field: 'type', headerName: 'Тип', width: 140 },
    {
      field: 'price',
      headerName: 'Цена',
      width: 140,
      valueFormatter: ({ value }) =>
        value === undefined || value === null ? '—' : `${Number(value).toLocaleString('ru-RU')} ₽`
    },
    {
      field: 'classes_count',
      headerName: 'Занятий',
      width: 120,
      valueGetter: (params) => params.row.classes_count ?? '—'
    },
    {
      field: 'validity_days',
      headerName: 'Дней действия',
      width: 140,
      valueGetter: (params) => params.row.validity_days ?? '—'
    },
    {
      field: 'is_active',
      headerName: 'Активен',
      type: 'boolean',
      width: 120
    },
    {
      field: 'actions',
      headerName: 'Действия',
      sortable: false,
      width: 220,
      renderCell: (params: GridRenderCellParams<Product>) => (
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={() => openEditDialog(params.row)}>
            Изменить
          </Button>
          <Button size="small" color="error" onClick={() => handleDelete(params.row)}>
            Удалить
          </Button>
        </Stack>
      )
    }
  ]

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
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button variant="contained" onClick={openCreateDialog}>
          Добавить продукт
        </Button>
      </Box>
      <Box height={500}>
        <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
      </Box>
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingProduct ? 'Редактирование продукта' : 'Новый продукт'}</DialogTitle>
        <DialogContent>
          <Box component="form" id="product-form" onSubmit={handleSubmit(onSubmit)}>
            <TextField
              label="Название"
              fullWidth
              margin="normal"
              {...register('name', { required: 'Укажите название' })}
              error={Boolean(formState.errors.name)}
              helperText={formState.errors.name?.message}
            />
            <TextField
              label="Тип"
              fullWidth
              margin="normal"
              {...register('type', { required: 'Укажите тип' })}
              error={Boolean(formState.errors.type)}
              helperText={formState.errors.type?.message}
            />
            <TextField
              label="Описание"
              fullWidth
              margin="normal"
              multiline
              minRows={2}
              {...register('description')}
            />
            <TextField
              label="Цена"
              type="number"
              fullWidth
              margin="normal"
              inputProps={{ step: '0.01' }}
              {...register('price', { required: 'Укажите цену', valueAsNumber: true })}
              error={Boolean(formState.errors.price)}
              helperText={formState.errors.price?.message}
            />
            <TextField
              label="Количество занятий"
              type="number"
              fullWidth
              margin="normal"
              {...register('classes_count', { valueAsNumber: true })}
            />
            <TextField
              label="Срок действия (дни)"
              type="number"
              fullWidth
              margin="normal"
              {...register('validity_days', { valueAsNumber: true })}
            />
            <TextField
              label="Ограничение по направлению (ID)"
              type="number"
              fullWidth
              margin="normal"
              {...register('direction_limit_id', { valueAsNumber: true })}
            />
            <Controller
              name="is_active"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={
                    <Switch
                      checked={field.value}
                      onChange={(_, checked) => field.onChange(checked)}
                    />
                  }
                  label="Активен"
                />
              )}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Отмена</Button>
          <Button type="submit" form="product-form" variant="contained" disabled={createMutation.isPending || updateMutation.isPending}>
            {editingProduct ? 'Сохранить' : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default ProductsPage
