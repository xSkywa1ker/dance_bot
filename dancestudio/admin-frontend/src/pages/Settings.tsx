import { ChangeEvent, useEffect, useRef, useState } from 'react'
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

type AddressMedia = {
  id: number
  url: string
  media_type: 'image' | 'video'
  filename: string
}

type StudioAddresses = {
  addresses: string
  media: AddressMedia[]
}

type SettingsUpdatePayload = SettingsForm & {
  media_ids: number[]
}

const SettingsPage = () => {
  const [media, setMedia] = useState<AddressMedia[]>([])
  const fileInputRef = useRef<HTMLInputElement | null>(null)

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
      setMedia(addressesQuery.data.media ?? [])
    }
  }, [addressesQuery.data, reset])

  const updateMutation = useMutation({
    mutationFn: async (payload: SettingsUpdatePayload) => {
      const { data } = await apiClient.put<StudioAddresses>('/settings/addresses', payload)
      return data
    },
    onSuccess: (data) => {
      reset({ addresses: data.addresses })
      setMedia(data.media ?? [])
    }
  })

  const uploadMutation = useMutation({
    mutationFn: async (files: FileList) => {
      const formData = new FormData()
      Array.from(files).forEach((file) => {
        formData.append('files', file)
      })
      const { data } = await apiClient.post<AddressMedia[]>(
        '/settings/addresses/media',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      )
      return data
    },
    onSuccess: (items) => {
      setMedia((prev) => [...prev, ...items])
    }
  })

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) {
      return
    }
    uploadMutation.mutate(files)
    event.target.value = ''
  }

  const handleRemoveMedia = (id: number) => {
    setMedia((prev) => prev.filter((item) => item.id !== id))
  }

  const onSubmit = (values: SettingsForm) => {
    updateMutation.mutate({
      addresses: values.addresses,
      media_ids: media.map((item) => item.id)
    })
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
        <Stack spacing={1}>
          <Typography variant="subtitle1">Фото и видео</Typography>
          {uploadMutation.isError && (
            <Alert severity="error">Не удалось загрузить файлы. Попробуйте ещё раз.</Alert>
          )}
          <Stack direction="row" spacing={2} flexWrap="wrap">
            {media.map((item) => (
              <Box key={item.id} width={160}>
                {item.media_type === 'video' ? (
                  <Box component="video" src={item.url} controls width="100%" />
                ) : (
                  <Box
                    component="img"
                    src={item.url}
                    alt={item.filename}
                    sx={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 1 }}
                  />
                )}
                <Typography variant="caption" noWrap title={item.filename}>
                  {item.filename}
                </Typography>
                <Button size="small" color="secondary" onClick={() => handleRemoveMedia(item.id)}>
                  Удалить
                </Button>
              </Box>
            ))}
            {media.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                Добавьте фото или видео, чтобы показать студию ученикам.
              </Typography>
            )}
          </Stack>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,video/*"
            hidden
            onChange={handleFileChange}
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              variant="outlined"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? 'Загрузка...' : 'Загрузить файлы'}
            </Button>
            <Typography variant="caption" color="text.secondary">
              Удалённые файлы исчезнут после сохранения настроек.
            </Typography>
          </Stack>
        </Stack>
        <Button type="submit" variant="contained" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
        </Button>
      </Stack>
    </Box>
  )
}

export default SettingsPage
