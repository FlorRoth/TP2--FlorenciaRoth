document.addEventListener("DOMContentLoaded", () => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const dniRegex = /^\d{7,8}$/;

  // Formulario Registro
  const formRegistro = document.getElementById("form-registro");
  if (formRegistro) {
    formRegistro.addEventListener("submit", (e) => {
      let valido = true;

      const nombre = document.getElementById("nombre");
      const dni = document.getElementById("dni");
      const email = document.getElementById("email");
      const password = document.getElementById("password");
      const password2 = document.getElementById("password2");

      const errNombre = document.getElementById("error-nombre");
      const errDni = document.getElementById("error-dni");
      const errEmail = document.getElementById("error-email");
      const errPass = document.getElementById("error-password");
      const errPass2 = document.getElementById("error-password2");

      [errNombre, errDni, errEmail, errPass, errPass2].forEach((el) => {
        if (el) el.textContent = "";
      });

      if (!nombre.value || nombre.value.trim().length < 3) {
        errNombre.textContent = "Ingresá tu nombre y apellido (mínimo 3 caracteres).";
        valido = false;
      }

      if (!dni.value || !dniRegex.test(dni.value.trim())) {
        errDni.textContent = "El DNI debe tener 7 u 8 números sin puntos.";
        valido = false;
      }

      if (!email.value || !emailRegex.test(email.value.trim())) {
        errEmail.textContent = "Ingresá un correo electrónico válido.";
        valido = false;
      }

      if (!password.value || password.value.length < 6) {
        errPass.textContent = "La contraseña debe tener al menos 6 caracteres.";
        valido = false;
      }

      if (password2.value !== password.value) {
        errPass2.textContent = "Las contraseñas no coinciden.";
        valido = false;
      }

      if (!valido) {
        e.preventDefault();
      }
    });
  }

  // Formulario Login
  const formLogin = document.getElementById("form-login");
  if (formLogin) {
    formLogin.addEventListener("submit", (e) => {
      let valido = true;

      const email = document.getElementById("email");
      const password = document.getElementById("password");
      const errEmail = document.getElementById("error-login-email");
      const errPass = document.getElementById("error-login-password");

      if (errEmail) errEmail.textContent = "";
      if (errPass) errPass.textContent = "";

      if (!email.value || !emailRegex.test(email.value.trim())) {
        errEmail.textContent = "Ingresá un correo electrónico con formato válido.";
        valido = false;
      }

      if (!password.value) {
        errPass.textContent = "Ingresá tu contraseña para continuar.";
        valido = false;
      }

      if (!valido) {
        e.preventDefault();
      }
    });
  }

  // Gestión de Turnos
  const selectEspecialidad = document.getElementById("especialidad");
  const inputFecha = document.getElementById("fecha");
  const selectHora = document.getElementById("hora");

  async function actualizarHorariosDisponibles() {
    if (!selectEspecialidad || !selectHora) return;

    const esp = selectEspecialidad.value;
    const fecha = inputFecha ? inputFecha.value : "";
    const horaPrevia = selectHora.dataset.horaPrevia || selectHora.value;

    if (!esp) {
      selectHora.innerHTML = '<option value="">Elegí especialidad y fecha</option>';
      return;
    }

    try {
      const url = `/api/horarios/${encodeURIComponent(esp)}?fecha=${encodeURIComponent(fecha)}`;
      const resp = await fetch(url);
      const data = await resp.json();

      if (data.ok) {
        selectHora.innerHTML = '<option value="">Seleccioná un horario</option>';
        data.horarios.forEach((h) => {
          const opt = document.createElement("option");
          opt.value = h;
          const estaOcupado = data.ocupados && data.ocupados.includes(h);
          if (estaOcupado) {
            opt.textContent = `${h} hs (Reservado)`;
            opt.disabled = true;
          } else {
            opt.textContent = `${h} hs`;
            if (h === horaPrevia) {
              opt.selected = true;
            }
          }
          selectHora.appendChild(opt);
        });
      }
    } catch (err) {
      console.error("Error al consultar horarios:", err);
    }
  }

  if (selectEspecialidad) {
    selectEspecialidad.addEventListener("change", actualizarHorariosDisponibles);
  }
  if (inputFecha) {
    inputFecha.addEventListener("change", actualizarHorariosDisponibles);
  }
  if (selectEspecialidad && selectEspecialidad.value) {
    actualizarHorariosDisponibles();
  }

  // IA
  const btnSugerirIA = document.getElementById("btn-sugerir-ia");
  if (btnSugerirIA) {
    btnSugerirIA.addEventListener("click", async () => {
      const campoMotivo = document.getElementById("motivo");
      const errMotivo = document.getElementById("error-motivo");
      const estadoIA = document.getElementById("estado-ia-inline");
      const panelIA = document.getElementById("panel-sugerencia-ia");

      if (errMotivo) errMotivo.textContent = "";

      const texto = campoMotivo ? campoMotivo.value.trim() : "";
      if (texto.length < 10) {
        if (errMotivo) {
          errMotivo.textContent =
            "Escribí primero tus síntomas (mínimo 10 caracteres) para que la IA pueda orientarte.";
        }
        return;
      }

      btnSugerirIA.disabled = true;
      if (estadoIA) estadoIA.textContent = "Analizando síntomas con IA...";

      try {
        const resp = await fetch("/api/orientacion-ia", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sintomas: texto }),
        });
        const data = await resp.json();

        if (!resp.ok || !data.ok) {
          if (errMotivo) errMotivo.textContent = data.error || "No se pudo consultar la IA.";
        } else {
          document.getElementById("ia-esp").textContent = data.especialidad;
          document.getElementById("ia-prof").textContent = data.profesional;
          const badgePrio = document.getElementById("ia-prio");
          badgePrio.textContent = data.prioridad;
          badgePrio.className =
            "badge " +
            (data.prioridad.includes("Alta")
              ? "badge-alta"
              : data.prioridad.includes("Media")
              ? "badge-media"
              : "badge-baja");
          document.getElementById("ia-rec").textContent = data.recomendacion;

          panelIA.classList.remove("oculto");

          
          if (selectEspecialidad) {
            selectEspecialidad.value = data.especialidad;
            await actualizarHorariosDisponibles();
          }
          if (estadoIA) {
            estadoIA.textContent = `Especialidad "${data.especialidad}" seleccionada automáticamente.`;
          }
        }
      } catch (error) {
        if (errMotivo) {
          errMotivo.textContent = "Error de conexión al consultar el servicio de IA.";
        }
      } finally {
        btnSugerirIA.disabled = false;
      }
    });
  }

  // Formulario de reserva de turno
  const formTurno = document.getElementById("form-turno");
  if (formTurno) {
    formTurno.addEventListener("submit", (e) => {
      let valido = true;

      const errMotivo = document.getElementById("error-motivo");
      const errEsp = document.getElementById("error-especialidad");
      const errFecha = document.getElementById("error-fecha");
      const errHora = document.getElementById("error-hora");

      [errMotivo, errEsp, errFecha, errHora].forEach((el) => {
        if (el) el.textContent = "";
      });

      if (!selectEspecialidad.value) {
        errEsp.textContent = "Seleccioná una especialidad médica.";
        valido = false;
      }

      if (!inputFecha.value) {
        errFecha.textContent = "Seleccioná la fecha para tu turno.";
        valido = false;
      } else {
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        const partes = inputFecha.value.split("-");
        const fechaElegida = new Date(
           Number(partes[0]),
          Number(partes[1]) - 1,
          Number(partes[2])
        );
        if (fechaElegida < hoy) {
          errFecha.textContent = "La fecha del turno no puede ser en el pasado.";
          valido = false;
        }
      }

      if (!selectHora.value) {
        errHora.textContent = "Seleccioná un horario disponible.";
        valido = false;
      }

      if (!valido) {
        e.preventDefault();
      }
    });
  }

  // Modal cancelar turno
  const modalCancelar = document.getElementById("modal-cancelar");
  const modalDetalle = document.getElementById("modal-detalle-turno");
  const btnCerrarModal = document.getElementById("btn-cerrar-modal");
  const btnConfirmarModal = document.getElementById("btn-confirmar-modal");
  let formularioACancelar = null;

  const formulariosCancelar = document.querySelectorAll(".form-cancelar");
  formulariosCancelar.forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmado === "true") {
        return;
      }
      e.preventDefault();
      formularioACancelar = form;
      if (modalDetalle) {
        modalDetalle.textContent = form.dataset.turno || "este turno";
      }
      if (modalCancelar) {
        modalCancelar.classList.remove("oculto");
      }
    });
  });

  if (btnCerrarModal && modalCancelar) {
    btnCerrarModal.addEventListener("click", () => {
      modalCancelar.classList.add("oculto");
      formularioACancelar = null;
    });
  }

  if (btnConfirmarModal) {
    btnConfirmarModal.addEventListener("click", () => {
      if (formularioACancelar) {
        formularioACancelar.dataset.confirmado = "true";
        formularioACancelar.submit();
      }
    });
  }

  if (modalCancelar) {
    modalCancelar.addEventListener("click", (e) => {
      if (e.target === modalCancelar) {
        modalCancelar.classList.add("oculto");
        formularioACancelar = null;
      }
    });
  }

  // Ejemplos rápidos y validación cliente 

  const botonesEjemplo = document.querySelectorAll(".boton-ejemplo");
  const campoSintomas = document.getElementById("sintomas");
  botonesEjemplo.forEach((boton) => {
    boton.addEventListener("click", () => {
      if (campoSintomas) {
        campoSintomas.value = boton.dataset.ejemplo || "";
        campoSintomas.focus();
      }
    });
  });

  const formAsistenteIA = document.getElementById("form-asistente-ia");
  if (formAsistenteIA) {
    formAsistenteIA.addEventListener("submit", (e) => {
      const errSintomas = document.getElementById("error-sintomas");
      if (errSintomas) errSintomas.textContent = "";

      if (!campoSintomas || campoSintomas.value.trim().length < 10) {
        if (errSintomas) {
          errSintomas.textContent =
            "Describí tus síntomas con al menos 10 caracteres para recibir la orientación de la IA.";
        }
        e.preventDefault();
      }
    });
  }
});

