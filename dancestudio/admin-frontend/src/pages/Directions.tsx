import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import {
  Box,
  CircularProgress,
  Alert,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  Stack
} from '@mui/material'
import { apiClient } from '../api/client'
import { Controller, useForm } from 'react-hook-form'

type Direction = {
  id: number
  name: string
  description?: string | null
  is_active: boolean
}

type DirectionFormValues = {
  name: string
  description: string
  is_active: boolean
}

const defaultValues: DirectionFormValues = {
  name: '',
  description: '',
  is_active: true
}

const DirectionsPage = () => {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingDirection, setEditingDirection] = useState<Direction | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['directions'],
    queryFn: async () => {
      const response = await apiClient.get<Direction[]>('/directions', {
        params: { include_inactive: true }
      })
      return response.data
    }
  })

  const { register, handleSubmit, reset, control, formState } = useForm<DirectionFormValues>({
    defaultValues
  })

  const openCreateDialog = () => {
    setEditingDirection(null)
    reset(defaultValues)
    setDialogOpen(true)
  }

  const openEditDialog = (direction: Direction) => {
    setEditingDirection(direction)
    reset({
      name: direction.name,
      description: direction.description ?? '',
      is_active: direction.is_active
    })
    setDialogOpen(true)
  }

  const closeDialog = () => setDialogOpen(false)

  const createMutation = useMutation({
    mutationFn: async (payload: DirectionFormValues) => {
      const response = await apiClient.post<Direction>('/directions', {
        ...payload,
        description: payload.description.trim() || null
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['directions'] })
      closeDialog()
    }
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: DirectionFormValues }) => {
      const response = await apiClient.patch<Direction>(`/directions/${id}`, {
        ...payload,
        description: payload.description.trim() || null
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['directions'] })
      closeDialog()
    }
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/directions/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['directions'] })
    }
  })

  const onSubmit = (values: DirectionFormValues) => {
    if (editingDirection) {
      updateMutation.mutate({ id: editingDirection.id, payload: values })
    } else {
      createMutation.mutate(values)
    }
  }

  const handleDelete = (direction: Direction) => {
    if (window.confirm(`Удалить направление «${direction.name}»?`)) {
      deleteMutation.mutate(direction.id)
    }
  }

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 90 },
    { field: 'name', headerName: 'Название', flex: 1, minWidth: 200 },
    { field: 'description', headerName: 'Описание', flex: 2, minWidth: 200 },
    { field: 'is_active', headerName: 'Активно', type: 'boolean', width: 120 },
    {
      field: 'actions',
      headerName: 'Действия',
      sortable: false,
      width: 220,
      renderCell: (params: GridRenderCellParams<Direction>) => (
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
    return <Alert severity="error">Не удалось загрузить направления</Alert>
  }

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button variant="contained" onClick={openCreateDialog}>
          Добавить направление
        </Button>
      </Box>
      <Box height={500}>
        <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
      </Box>
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingDirection ? 'Редактирование направления' : 'Новое направление'}</DialogTitle>
        <DialogContent>
          <Box component="form" id="direction-form" onSubmit={handleSubmit(onSubmit)}>
            <TextField
              label="Название"
              fullWidth
              margin="normal"
              {...register('name', { required: 'Укажите название' })}
              error={Boolean(formState.errors.name)}
              helperText={formState.errors.name?.message}
            />
            <TextField
              label="Описание"
              fullWidth
              margin="normal"
              multiline
              minRows={2}
              {...register('description')}
            />
            <Controller
              name="is_active"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Switch checked={field.value} onChange={(_, checked) => field.onChange(checked)} />}
                  label="Активно"
                />
              )}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Отмена</Button>
          <Button
            type="submit"
            form="direction-form"
            variant="contained"
            disabled={createMutation.isPending || updateMutation.isPending}
          >
            {editingDirection ? 'Сохранить' : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default DirectionsPage
