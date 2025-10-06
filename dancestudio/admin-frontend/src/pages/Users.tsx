import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import {
  Alert,
  CircularProgress,
  Box,
  Stack,
  TextField,
  Button,
  Typography,
  Paper,
  List,
  ListItemButton,
  ListItemText
} from '@mui/material'
import { apiClient } from '../api/client'
import { DataGrid, GridColDef } from '@mui/x-data-grid'

interface User {
  id: number
  full_name?: string
  tg_id: number
  age?: number
  phone?: string
}

interface ManualSubscriptionForm {
  classesCount: number
  validityDays?: number
}

const columns: GridColDef<User>[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'full_name', headerName: 'Имя', flex: 1 },
  { field: 'tg_id', headerName: 'Telegram ID', width: 150 },
  { field: 'age', headerName: 'Возраст', width: 120 },
  { field: 'phone', headerName: 'Телефон', width: 150 }
]

const UsersPage = () => {
  const [search, setSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await apiClient.get<User[]>('/users')
      return response.data
    }
  })

  const searchQuery = useQuery({
    queryKey: ['user-search', search],
    queryFn: async () => {
      const response = await apiClient.get<User[]>('/users/search', {
        params: { q: search }
      })
      return response.data
    },
    enabled: search.trim().length >= 2
  })

  const {
    register,
    handleSubmit,
    reset: resetSubscriptionForm
  } = useForm<ManualSubscriptionForm>({
    defaultValues: { classesCount: 1, validityDays: 90 }
  })

  const grantMutation = useMutation({
    mutationFn: async (values: ManualSubscriptionForm) => {
      if (!selectedUser) {
        throw new Error('Пользователь не выбран')
      }
      const payload: { classes_count: number; validity_days?: number } = {
        classes_count: values.classesCount
      }
      if (values.validityDays && values.validityDays > 0) {
        payload.validity_days = values.validityDays
      }
      const { data: subscription } = await apiClient.post(
        `/users/${selectedUser.id}/manual-subscription`,
        payload
      )
      return subscription
    },
    onSuccess: () => {
      resetSubscriptionForm({ classesCount: 1, validityDays: 90 })
    }
  })

  const onGrant = handleSubmit((values) => {
    grantMutation.mutate(values)
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
    <Stack spacing={4}>
      <Stack spacing={2}>
        <Typography variant="h6">Выдать абонемент вручную</Typography>
        <Stack spacing={1} maxWidth={480}>
          <TextField
            label="Поиск по ФИО"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            helperText="Введите минимум 2 символа"
          />
          {search.trim().length >= 2 && (
            <Paper variant="outlined">
              {searchQuery.isFetching && (
                <Typography variant="body2" px={2} py={1} color="text.secondary">
                  Поиск...
                </Typography>
              )}
              {!searchQuery.isFetching && (searchQuery.data?.length ?? 0) === 0 && (
                <Typography variant="body2" px={2} py={1} color="text.secondary">
                  Пользователи не найдены
                </Typography>
              )}
              <List dense disablePadding>
                {searchQuery.data?.map((user) => (
                  <ListItemButton
                    key={user.id}
                    selected={selectedUser?.id === user.id}
                    onClick={() => setSelectedUser(user)}
                  >
                    <ListItemText
                      primary={user.full_name || `ID ${user.id}`}
                      secondary={`Telegram ID: ${user.tg_id}`}
                    />
                  </ListItemButton>
                ))}
              </List>
            </Paper>
          )}
        </Stack>
        {selectedUser && (
          <Typography variant="body2" color="text.secondary">
            Выбран пользователь: {selectedUser.full_name || `ID ${selectedUser.id}`} · Telegram ID:{' '}
            {selectedUser.tg_id}
          </Typography>
        )}
        <Box component="form" onSubmit={onGrant} maxWidth={480}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-end">
            <TextField
              label="Количество занятий"
              type="number"
              inputProps={{ min: 1 }}
              {...register('classesCount', {
                valueAsNumber: true,
                min: 1
              })}
            />
            <TextField
              label="Срок действия (дней)"
              type="number"
              inputProps={{ min: 1 }}
              {...register('validityDays', {
                setValueAs: (value) => (value === '' ? undefined : Number(value))
              })}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={!selectedUser || grantMutation.isPending}
            >
              {grantMutation.isPending ? 'Выдаём...' : 'Выдать'}
            </Button>
          </Stack>
        </Box>
        {grantMutation.isError && (
          <Alert severity="error">Не удалось выдать абонемент. Попробуйте ещё раз.</Alert>
        )}
        {grantMutation.isSuccess && !grantMutation.isPending && (
          <Alert severity="success">Абонемент успешно выдан.</Alert>
        )}
      </Stack>
      <Box height={400}>
        <DataGrid rows={data ?? []} columns={columns} disableRowSelectionOnClick />
      </Box>
    </Stack>
  )
}

export default UsersPage
