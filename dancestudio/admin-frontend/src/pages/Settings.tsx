import { useEffect } from 'react'
import {
  Box,
  TextField,
  Button,
  Stack,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { apiClient } from '../api/client'

type SettingsForm = {
  addresses: string
}

type StudioAddresses = {
  addresses: string
}

const SettingsPage = () => {
  const { register, handleSubmit, reset } = useForm<SettingsForm>({
    defaultValues: {
      addresses: ''
    }
  })

  const addressesQuery = useQuery({
    queryKey: ['studio-addresses'],
    queryFn: async () => {
      const { data } = await apiClient.get<StudioAddresses>('/settings/addresses')
      return data
    }
  })

  useEffect(() => {
    if (addressesQuery.data) {
      reset({ addresses: addressesQuery.data.addresses })
    }
  }, [addressesQuery.data, reset])

  const updateMutation = useMutation({
    mutationFn: async (payload: SettingsForm) => {
      const { data } = await apiClient.put<StudioAddresses>('/settings/addresses', payload)
      return data
    },
    onSuccess: (data) => {
      reset({ addresses: data.addresses })
    }
  })

  const onSubmit = (values: SettingsForm) => {
    updateMutation.mutate(values)
  }

  if (addressesQuery.isLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    )
  }

  if (addressesQuery.error) {
    return <Alert severity="error">Не удалось загрузить адреса. Попробуйте позже.</Alert>
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} maxWidth={600}>
      <Stack spacing={2}>
        <Typography variant="h6">Наши адреса</Typography>
        {updateMutation.isError && (
          <Alert severity="error">Не удалось сохранить адреса. Попробуйте ещё раз.</Alert>
        )}
        {updateMutation.isSuccess && !updateMutation.isPending && (
          <Alert severity="success">Адреса обновлены.</Alert>
        )}
        <TextField
          label="Список адресов"
          multiline
          minRows={4}
          {...register('addresses')}
        />
        <Button type="submit" variant="contained" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
        </Button>
      </Stack>
    </Box>
  )
}

export default SettingsPage
