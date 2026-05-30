/**
 * Dynamic Django formset for debate participants.
 * Expects #participants-formset with data-prefix, data-min, data-max.
 */
(function () {
    'use strict';

    const container = document.getElementById(
        'participants-formset',
    );

    if (!container) {
        return;
    }

    const formsetPrefix = container.dataset.prefix;

    const minParticipants = Number.parseInt(
        container.dataset.min,
        10,
    );

    const maxParticipants = Number.parseInt(
        container.dataset.max,
        10,
    );

    const totalFormsInput = document.getElementById(
        `id_${formsetPrefix}-TOTAL_FORMS`,
    );

    const addButton = document.getElementById(
        'add-participant',
    );

    const countLabel = document.getElementById(
        'participant-count-label',
    );

    const emptyTemplate = document.getElementById(
        'empty-participant-template',
    );

    if (
        !formsetPrefix
        || !totalFormsInput
        || !addButton
        || !countLabel
        || !emptyTemplate
    ) {
        console.error(
            'Participant formset: missing required DOM nodes.',
            {
                formsetPrefix,
                totalFormsInput,
                addButton,
                countLabel,
                emptyTemplate,
            },
        );
        return;
    }

    const fieldNamePattern = new RegExp(
        `^${escapeRegExp(formsetPrefix)}-\\d+-`,
    );

    const fieldIdPattern = new RegExp(
        `^id_${escapeRegExp(formsetPrefix)}-\\d+-`,
    );

    function escapeRegExp(value) {
        return value.replace(
            /[.*+?^${}()|[\]\\]/g,
            '\\$&',
        );
    }

    function getRows() {
        return container.querySelectorAll(
            '.participant-row',
        );
    }

    function syncTotalForms() {
        totalFormsInput.value = String(
            getRows().length,
        );
    }

    function updateCountLabel() {
        const count = getRows().length;

        countLabel.textContent = (
            `${count} / ${maxParticipants}`
        );

        addButton.disabled = (
            count >= maxParticipants
        );
    }

    function updateRemoveButtons() {
        const count = getRows().length;
        const canRemove = (
            count > minParticipants
        );

        getRows().forEach((row) => {
            const button = row.querySelector(
                '.remove-participant',
            );

            if (button) {
                button.disabled = !canRemove;
            }
        });
    }

    function renumberRows() {
        getRows().forEach((row, index) => {
            const numberNode = row.querySelector(
                '.participant-number',
            );

            if (numberNode) {
                numberNode.textContent = String(
                    index + 1,
                );
            }

            row.querySelectorAll(
                'input, select, textarea',
            ).forEach((field) => {
                if (!field.name) {
                    return;
                }

                field.name = field.name.replace(
                    fieldNamePattern,
                    `${formsetPrefix}-${index}-`,
                );

                if (field.id) {
                    field.id = field.id.replace(
                        fieldIdPattern,
                        `id_${formsetPrefix}-${index}-`,
                    );
                }
            });
        });

        syncTotalForms();
        updateCountLabel();
        updateRemoveButtons();
    }

    function addParticipantRow() {
        if (
            getRows().length
            >= maxParticipants
        ) {
            return;
        }

        const index = getRows().length;

        let html = emptyTemplate.innerHTML;

        html = html.replace(
            /__prefix__/g,
            String(index),
        );

        html = html.replace(
            /__num__/g,
            String(index + 1),
        );

        const wrapper = document.createElement(
            'div',
        );

        wrapper.innerHTML = html.trim();

        const row = wrapper.firstElementChild;

        if (!row) {
            return;
        }

        container.appendChild(row);
        renumberRows();
    }

    function removeParticipantRow(row) {
        if (
            getRows().length
            <= minParticipants
        ) {
            return;
        }

        row.remove();
        renumberRows();
    }

    container.addEventListener(
        'click',
        (event) => {
            const button = event.target.closest(
                '.remove-participant',
            );

            if (!button || button.disabled) {
                return;
            }

            const row = button.closest(
                '.participant-row',
            );

            if (!row) {
                return;
            }

            event.preventDefault();
            removeParticipantRow(row);
        },
    );

    addButton.addEventListener(
        'click',
        (event) => {
            event.preventDefault();
            addParticipantRow();
        },
    );

    renumberRows();
})();
