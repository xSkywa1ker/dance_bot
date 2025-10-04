import { useMemo, useState } from 'react'
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
  FormControlLabel,
  Switch,
  MenuItem,
  Stack
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs, { type Dayjs } from 'dayjs'
import { Controller, useForm } from 'react-hook-form'

interface Direction {
  id: number
  name: string
}

interface Slot {
  id: number
  direction_id: number
  starts_at: string
  duration_min: number
  capacity: number
  price_single_visit: number
  allow_subscription: boolean
  status: string
}

type SlotFormValues = {
  direction_id: number
  starts_at: string
  duration_min: number
  capacity: number
  price_single_visit: number
  allow_subscription: boolean
  status: string
}

const slotDefaultValues: SlotFormValues = {
  direction_id: 0,
  starts_at: dayjs().startOf('hour').format('YYYY-MM-DDTHH:mm'),
  duration_min: 60,
  capacity: 10,
  price_single_visit: 0,
  allow_subscription: true,
  status: 'scheduled'
}

const SchedulePage = () => {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingSlot, setEditingSlot] = useState<Slot | null>(null)
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(dayjs())
  const [cancelingSlotId, setCancelingSlotId] = useState<number | null>(null)

  const directionsQuery = useQuery({
    queryKey: ['directions'],
    queryFn: async () => {
      const response = await apiClient.get<Direction[]>('/directions', {
        params: { include_inactive: true }
      })
      return response.data
    }
  })

  const slotsQuery = useQuery({
    queryKey: ['slots', selectedDate ? selectedDate.format('YYYY-MM-DD') : 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (selectedDate) {
        params.from_dt = selectedDate.startOf('day').toISOString()
        params.to_dt = selectedDate.endOf('day').toISOString()
      }
      const response = await apiClient.get<Slot[]>('/slots', { params })
      return response.data
    }
  })

  const { register, handleSubmit, reset, control, formState } = useForm<SlotFormValues>({
    defaultValues: slotDefaultValues
  })

  const openCreateDialog = () => {
    if (!directionsQuery.data || directionsQuery.data.length === 0) {
      return
    }
    setEditingSlot(null)
    const firstDirection = directionsQuery.data[0]
    const referenceTime = dayjs().startOf('hour')
    const defaultStart = selectedDate
      ? selectedDate.set('hour', referenceTime.hour()).set('minute', referenceTime.minute())
      : referenceTime
    reset({
      ...slotDefaultValues,
      direction_id: firstDirection.id,
      starts_at: defaultStart.format('YYYY-MM-DDTHH:mm')
    })
    setDialogOpen(true)
  }

  const openEditDialog = (slot: Slot) => {
    setEditingSlot(slot)
    reset({
      direction_id: slot.direction_id,
      starts_at: dayjs(slot.starts_at).format('YYYY-MM-DDTHH:mm'),
      duration_min: slot.duration_min,
      capacity: slot.capacity,
      price_single_visit: Number(slot.price_single_visit),
      allow_subscription: slot.allow_subscription,
      status: slot.status
    })
    setDialogOpen(true)
  }

  const closeDialog = () => setDialogOpen(false)

  const createMutation = useMutation({
    mutationFn: async (payload: SlotFormValues) => {
      const response = await apiClient.post<Slot>('/slots', {
        ...payload,
        starts_at: dayjs(payload.starts_at).toISOString()
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slots'] })
      closeDialog()
    }
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: SlotFormValues }) => {
      const response = await apiClient.patch<Slot>(`/slots/${id}`, {
        ...payload,
        starts_at: dayjs(payload.starts_at).toISOString()
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slots'] })
      closeDialog()
    }
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/slots/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slots'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await apiClient.post<Slot>(`/slots/${id}/cancel`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slots'] })
    },
    onSettled: () => {
      setCancelingSlotId(null)
    }
  })

  const onSubmit = (values: SlotFormValues) => {
    const payload: SlotFormValues = {
      ...values,
      price_single_visit: Number(values.price_single_visit)
    }
    if (editingSlot) {
      updateMutation.mutate({ id: editingSlot.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleDelete = (slot: Slot) => {
    if (window.confirm('Удалить занятие из расписания?')) {
      deleteMutation.mutate(slot.id)
    }
  }

  const handleCancel = (slot: Slot) => {
    if (slot.status === 'canceled') {
      return
    }
    if (window.confirm('Отменить это занятие?')) {
      setCancelingSlotId(slot.id)
      cancelMutation.mutate(slot.id)
    }
  }

  const directionsMap = useMemo(() => {
    const map = new Map<number, string>()
    directionsQuery.data?.forEach((direction) => {
      map.set(direction.id, direction.name)
    })
    return map
  }, [directionsQuery.data])

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 80 },
    {
      field: 'direction_id',
      headerName: 'Направление',
      flex: 1,
      minWidth: 180,
      valueGetter: (params) => directionsMap.get(params.row.direction_id) ?? '—'
    },
    {
      field: 'starts_at',
      headerName: 'Начало',
      flex: 1,
      minWidth: 180,
      valueFormatter: ({ value }) => dayjs(value as string).format('DD.MM.YYYY HH:mm')
    },
    {
      field: 'duration_min',
      headerName: 'Длительность, мин',
      width: 150
    },
    { field: 'capacity', headerName: 'Мест', width: 100 },
    {
      field: 'price_single_visit',
      headerName: 'Разовое посещение',
      width: 180,
      valueFormatter: ({ value }) =>
        value === undefined || value === null ? '—' : `${Number(value).toFixed(2)} ₽`
    },
    {
      field: 'allow_subscription',
      headerName: 'Абонемент',
      type: 'boolean',
      width: 140
    },
    { field: 'status', headerName: 'Статус', width: 140 },
    {
      field: 'actions',
      headerName: 'Действия',
      sortable: false,
      width: 340,
      renderCell: (params: GridRenderCellParams<Slot>) => (
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={() => openEditDialog(params.row)}>
            Изменить
          </Button>
          <Button
            size="small"
            color="warning"
            disabled={params.row.status === 'canceled' || cancelMutation.isPending}
            onClick={() => handleCancel(params.row)}
          >
            {cancelMutation.isPending && cancelingSlotId === params.row.id
              ? 'Отмена...'
              : 'Отменить'}
          </Button>
          <Button size="small" color="error" onClick={() => handleDelete(params.row)}>
            Удалить
          </Button>
        </Stack>
      )
    }
  ]

  if (directionsQuery.isLoading || slotsQuery.isLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    )
  }

  if (directionsQuery.error || slotsQuery.error) {
    return <Alert severity="error">Не удалось загрузить расписание</Alert>
  }

  const directionOptions = directionsQuery.data ?? []
  const hasDirections = directionOptions.length > 0

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box>
        <Stack
          direction={{ xs: 'column', lg: 'row' }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: 'stretch', lg: 'center' }}
          mb={2}
        >
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            sx={{ flexWrap: 'wrap' }}
          >
            <DatePicker
              label="Дата занятий"
              value={selectedDate}
              onChange={(date) => setSelectedDate(date)}
              format="DD.MM.YYYY"
              slotProps={{
                textField: {
                  size: 'small',
                  sx: { minWidth: 220 }
                }
              }}
            />
            <Button variant="outlined" size="small" onClick={() => setSelectedDate(dayjs())}>
              Сегодня
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setSelectedDate(null)}
              disabled={!selectedDate}
            >
              Показать все
            </Button>
          </Stack>
          <Button variant="contained" onClick={openCreateDialog} disabled={!hasDirections}>
            Добавить занятие
          </Button>
        </Stack>
        {!hasDirections ? (
          <Alert severity="info">Добавьте направление, чтобы создать расписание.</Alert>
        ) : (
          <Box height={500}>
            <DataGrid
              rows={slotsQuery.data ?? []}
              columns={columns}
              disableRowSelectionOnClick
              loading={slotsQuery.isFetching}
            />
          </Box>
        )}
        <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
          <DialogTitle>{editingSlot ? 'Редактирование занятия' : 'Новое занятие'}</DialogTitle>
          <DialogContent>
            <Box component="form" id="slot-form" onSubmit={handleSubmit(onSubmit)}>
              <TextField
                select
                label="Направление"
                fullWidth
                margin="normal"
                {...register('direction_id', {
                  required: 'Выберите направление',
                  valueAsNumber: true,
                  validate: (value) => value > 0 || 'Выберите направление'
                })}
                error={Boolean(formState.errors.direction_id)}
                helperText={formState.errors.direction_id?.message}
              >
                {directionOptions.map((direction) => (
                  <MenuItem key={direction.id} value={direction.id}>
                    {direction.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Дата и время начала"
                type="datetime-local"
                fullWidth
                margin="normal"
                InputLabelProps={{ shrink: true }}
                {...register('starts_at', { required: 'Укажите дату и время' })}
                error={Boolean(formState.errors.starts_at)}
                helperText={formState.errors.starts_at?.message}
              />
              <TextField
                label="Длительность (мин)"
                type="number"
                fullWidth
                margin="normal"
                {...register('duration_min', { required: 'Укажите длительность', valueAsNumber: true })}
                error={Boolean(formState.errors.duration_min)}
                helperText={formState.errors.duration_min?.message}
              />
              <TextField
                label="Количество мест"
                type="number"
                fullWidth
                margin="normal"
                {...register('capacity', { required: 'Укажите количество мест', valueAsNumber: true })}
                error={Boolean(formState.errors.capacity)}
                helperText={formState.errors.capacity?.message}
              />
              <TextField
                label="Стоимость разового посещения"
                type="number"
                fullWidth
                margin="normal"
                inputProps={{ step: '0.01' }}
                {...register('price_single_visit', { required: 'Укажите стоимость', valueAsNumber: true })}
                error={Boolean(formState.errors.price_single_visit)}
                helperText={formState.errors.price_single_visit?.message}
              />
              <Controller
                name="allow_subscription"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={<Switch checked={field.value} onChange={(_, checked) => field.onChange(checked)} />}
                    label="Доступно по абонементу"
                  />
                )}
              />
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <TextField select label="Статус" fullWidth margin="normal" {...field}>
                    <MenuItem value="scheduled">Запланировано</MenuItem>
                    <MenuItem value="canceled">Отменено</MenuItem>
                    <MenuItem value="completed">Проведено</MenuItem>
                  </TextField>
                )}
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeDialog}>Отмена</Button>
            <Button
              type="submit"
              form="slot-form"
              variant="contained"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editingSlot ? 'Сохранить' : 'Добавить'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  )
}

export default SchedulePage
