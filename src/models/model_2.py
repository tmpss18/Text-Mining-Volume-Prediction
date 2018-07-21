from argparse import ArgumentParser

from keras import Input, Model
from keras.layers import Embedding, Dense, Conv1D, GlobalMaxPooling1D, \
    Concatenate

from src.encoder.glove import Glove
from src.models.model_builder import ModelBuilder
from src.models.preprocessor import Preprocessor
from src.utils.calculate_class_weights import calculate_class_weights
from src.utils.f1_score import precision, recall, f1
from src.utils.logging.callback_builder import CallbackBuilder
from src.utils.logging.callbacks.config_logger import ConfigLogger
from src.utils.logging.callbacks.csv_logger import CsvLogger
from src.utils.logging.callbacks.csv_plotter import CsvPlotter
from src.utils.logging.callbacks.model_saver import ModelSaver
from src.utils.settings import Settings


class Model2Builder(ModelBuilder):
    def __init__(self):
        super().__init__()
        settings = Settings()

        self.required_inputs.append('glove')
        self.required_parameters.append('max_headline_length')

        self.default_parameters['filter_count_5'] = settings.get_network_parameters('filter_count_5')
        self.default_parameters['filter_count_3'] = settings.get_network_parameters('filter_count_3')
        self.default_parameters['filter_count_1'] = settings.get_network_parameters('filter_count_1')

        self.default_parameters['optimizer'] = settings.get_network_parameters('optimizer')
        self.default_parameters['loss'] = settings.get_network_parameters('loss_function')

    def __call__(self):
        super().prepare_building()

        glove = self.inputs['glove']
        headline_input = Input(shape=(self.parameters['max_headline_length'],), name='headline_input')
        headline_embedding = Embedding(glove.embedding_vectors.shape[0],
                                       glove.embedding_vectors.shape[1],
                                       weights=[glove.embedding_vectors])(headline_input)

        convolution_5 = Conv1D(self.parameters['filter_count_5'], kernel_size=5)(headline_embedding)
        convolution_5_max = GlobalMaxPooling1D()(convolution_5)
        convolution_3 = Conv1D(self.parameters['filter_count_3'], kernel_size=3)(headline_embedding)
        convolution_3_max = GlobalMaxPooling1D()(convolution_3)
        convolution_1 = Conv1D(self.parameters['filter_count_1'], kernel_size=1)(headline_embedding)
        convolution_1_max = GlobalMaxPooling1D()(convolution_1)

        concat = Concatenate()([convolution_5_max, convolution_3_max, convolution_1_max])
        main_output = Dense(1, activation='sigmoid', name='output')(concat)

        model = Model(inputs=[headline_input], outputs=[main_output], name=self.model_identifier)

        model.compile(loss=self.parameters['loss'],
                      optimizer=self.parameters['optimizer'],
                      metrics=['accuracy', precision, recall, f1])

        return model

    @property
    def model_identifier(self):
        return 'model_2'


def train():
    settings = Settings()

    batch_size = settings.get_training_parameters('batch_size')
    epochs = settings.get_training_parameters('epochs')
    dictionary_size = settings.get_training_parameters('dictionary_size')
    max_headline_length = settings.get_training_parameters('max_headline_length')

    glove = Glove(dictionary_size)
    glove.load_embedding()

    model_builder = Model2Builder() \
        .set_input('glove', glove) \
        .set_parameter('max_headline_length', max_headline_length)

    model = model_builder()

    preprocessor = Preprocessor(model)
    preprocessor.set_encoder('glove', glove)
    preprocessor.set_parameter('max_headline_length', max_headline_length)

    preprocessor.load_data(['headline', 'is_top_submission'])

    training_input = [preprocessor.training_data['headline']]
    validation_input = [preprocessor.validation_data['headline']]
    training_output = [preprocessor.training_data['is_top_submission']]
    validation_output = [preprocessor.validation_data['is_top_submission']]

    class_weights = calculate_class_weights(preprocessor.training_data['is_top_submission'],
                                            [ol.name for ol in model.output_layers])

    callbacks = CallbackBuilder(model, [CsvLogger, CsvPlotter, ConfigLogger, ModelSaver])()

    model.fit(training_input, training_output, batch_size=batch_size, epochs=epochs,
              callbacks=callbacks, validation_data=(validation_input, validation_output), class_weight=class_weights)
