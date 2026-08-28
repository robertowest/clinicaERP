"""introduce `Rol` (proxy de `auth.Group`), `RolPerfil` y `PermisoPersonalizado`, y migra
`UsuarioClinica.rol` de `CharField(choices=...)` hardcodeado a `ForeignKey(Rol)`.

la conversión de tipo (string -> fk) no es segura como un `AlterField` directo (sqlite
recrearía la columna intentando volcar valores como "DOCTOR" en una fk entera), así que se
hace en varios pasos dentro de la misma migración: se añade la fk nueva en paralelo, se
rellena con datos (traduciendo el string antiguo a través del catálogo de roles, creado
aquí mismo si no existe todavía) y solo entonces se retira la columna vieja.

nota: `poblar_roles_y_migrar_asignaciones` importa `apps.usuarios.services` (código "vivo",
no los modelos históricos de la migración) para reutilizar `crear_catalogo_roles()` sin
duplicar el catálogo aquí. es un compromiso deliberado: en este proyecto no hay todavía
ningún entorno con datos reales (fase de bootstrap), así que se prioriza no duplicar la
lógica del catálogo sobre la pureza de operar solo con modelos históricos.
"""
import django.contrib.auth.models
import django.db.models.deletion
from django.db import migrations, models


def poblar_roles_y_migrar_asignaciones(apps, schema_editor):
    from apps.usuarios.services import crear_catalogo_roles

    roles_por_codigo = crear_catalogo_roles()

    UsuarioClinica = apps.get_model('usuarios', 'UsuarioClinica')
    for asignacion in UsuarioClinica.objects.all():
        rol = roles_por_codigo.get(asignacion.rol)
        if rol is None:
            # código retirado (el antiguo SUPERADMIN, que ya no es un rol asignable: lo
            # cubre `CustomUser.is_superuser`) o dato huérfano: se descarta. no hay
            # entornos con datos reales todavía.
            asignacion.delete()
            continue
        UsuarioClinica.objects.filter(pk=asignacion.pk).update(rol_nuevo_id=rol.id)


def revertir_poblado(apps, schema_editor):
    """no-op: revertir la traducción de fk a string no es necesario, `RemoveField`/
    `RenameField` al revertirse ya devuelven el esquema al estado anterior; los datos no
    se restauran (no hay entornos con datos reales todavía)."""


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('usuarios', '0003_alter_customuser_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermisoPersonalizado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'permiso personalizado',
                'verbose_name_plural': 'permisos personalizados',
                'managed': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Rol',
            fields=[
            ],
            options={
                'verbose_name': 'rol',
                'verbose_name_plural': 'roles',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.group',),
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name='RolPerfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='identificador estable del rol (ver apps.usuarios.roles.Roles); no cambia aunque se renombre el rol desde el admin.', max_length=20, unique=True, verbose_name='código')),
                ('requiere_clinica', models.BooleanField(default=True, help_text='si el rol es de alcance grupo/plataforma (ej. administrador de grupo), desmarcar: sus asignaciones no llevan clínica concreta.', verbose_name='requiere clínica')),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to='usuarios.rol', verbose_name='rol')),
            ],
            options={
                'verbose_name': 'perfil de rol',
                'verbose_name_plural': 'perfiles de rol',
                'db_table': 'usua_rol_perfiles',
                'ordering': ['codigo'],
            },
        ),
        migrations.AddField(
            model_name='usuarioclinica',
            name='rol_nuevo',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='asignaciones', to='usuarios.rol', verbose_name='rol',
            ),
        ),
        migrations.RunPython(poblar_roles_y_migrar_asignaciones, revertir_poblado),
        migrations.RemoveField(
            model_name='usuarioclinica',
            name='rol',
        ),
        migrations.RenameField(
            model_name='usuarioclinica',
            old_name='rol_nuevo',
            new_name='rol',
        ),
        migrations.AlterField(
            model_name='usuarioclinica',
            name='rol',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='asignaciones', to='usuarios.rol', verbose_name='rol',
            ),
        ),
    ]
