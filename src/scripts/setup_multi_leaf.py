if __name__ == '__main__':  # needed to circumvent multiprocessing RuntimeError under Windows 10
    from src.InterpretableSpn import InterpretableSpn
    from src.influence.dataset import DataSet  # for train and test set creation
    from tensorflow.contrib.learn.python.learn.datasets import base
    from spn.structure.leaves.parametric.Parametric import Gaussian, Categorical  # for SPN structure
    import numpy as np
    from src.help_functions import *

    # Generate dummy data sets (at least 5 instances needed for HVP, why ever)
    train_set = DataSet(np.array([[1.0], [1.5], [0.9], [0.77], [0.66], [1.15]], dtype=np.float32),
                        np.array([[1], [1], [0], [0], [0], [1]], dtype=np.float32))
    test_samples = np.array([[1.9], [0.4]], dtype=np.float32)
    test_labels = np.array([[1], [0]], dtype=np.float32)
    test_set = DataSet(test_samples, test_labels)
    validation_set = None

    # Collect SPN attributes
    data_sets = base.Datasets(train=train_set, test=test_set, validation=validation_set)
    model_name = "Multi-leaf SPN"
    input_dim = 2
    batch_size = 1

    # Construct multi-leaf SPN
    # Throws LookupError because Categorical is not twice differentiable
    multi_leaf_spn = 0.1 * (Gaussian(mean=[0.67], stdev=[0.22], scope=0) *
                            Categorical(p=[0.2, 0.8], scope=1)) \
                     + 0.9 * (Gaussian(mean=[0.39], stdev=[0.99], scope=0) *
                              Categorical(p=[0.2, 0.8], scope=1))
    '''
    multi_leaf_spn = 0.1 * (Gaussian(mean=[0.67], stdev=[0.22], scope=0) *
                            Gaussian(mean=[0.57], stdev=[0.11], scope=1)) \
                     + 0.9 * (Gaussian(mean=[0.39], stdev=[0.99], scope=0) *
                              Gaussian(mean=[0.07], stdev=[0.18], scope=1))'''

    # Convert this SPN into a tf.Tensor (test_samples needed for shape)
    single_leaf_spn_tensor, data_placeholder, _ = convert_spn_to_tf_graph(multi_leaf_spn,
                                                                          np.concatenate((test_samples, test_labels),
                                                                                         axis=1),
                                                                          batch_size,
                                                                          dtype=np.float32)

    root = tf.identity(single_leaf_spn_tensor, name="Root")

    '''
    sample_placeholder = data_placeholder[:, 0]
    label_placeholder = data_placeholder[:, 1]'''

    # Export the model
    export_dir = "output/converted_single_leaf_spn"
    export_dir = export_model(export_dir=export_dir)

    tf.reset_default_graph()

    # Import the model with new placeholders
    sample_placeholder = tf.placeholder(dtype=np.float32,
                                        shape=(batch_size, test_samples.shape[1]),
                                        name="Sample_Placeholder")
    label_placeholder = tf.placeholder(dtype=np.float32,
                                       shape=(batch_size, test_labels.shape[1]),
                                       name="Label_Placeholder")
    # no_gradient = tf.stop_gradient(label_placeholder)
    input_placeholder = tf.concat([sample_placeholder, label_placeholder], 1)
    input_map = {"Placeholder:0": input_placeholder}
    restored_spn_graph = import_model(export_dir, input_map)
    root = restored_spn_graph.get_tensor_by_name("Root:0")

    # Create a graph log to visualize graph with TensorBoard
    plot_tf_graph(root, {sample_placeholder: [test_samples[1]],
                         label_placeholder: [test_labels[1]]})

    # Initialize single-leaf SPN
    interpretable_spn = InterpretableSpn(root_node=root,
                                         input_placeholder=sample_placeholder,
                                         label_placeholder=label_placeholder,
                                         data_sets=data_sets,
                                         input_dim=input_dim,
                                         num_classes=1,
                                         label_idx=0,
                                         batch_size=batch_size,
                                         num_epochs=15,
                                         model_name=model_name,
                                         train_dir='output',
                                         mini_batch=False)

    influence = interpretable_spn.get_influence_on_test_loss(test_indices=[1],
                                                             train_idx=[0],
                                                             ignore_hessian=False)
    print("Influence on test loss:", influence)

    influence_grad = interpretable_spn.get_grad_of_influence_wrt_input(test_indices=[0], train_indices=[0])
    print("Influence gradient:", influence_grad)
